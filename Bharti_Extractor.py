"""
Bharti Invoice Extractor (Unified)
Extracts item details from Bharti Airtel and Bharti Hexacom PDF Invoices.
Supports Ceragon, Ciena, and ECI formats automatically.

Developed for Nagarkot Forwarders Pvt Ltd.
"""

import os
import sys
import datetime
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import re
import pdfplumber

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Design System & Colors (Nagarkot Corporate Colors)
# ---------------------------------------------------------------------------
BRAND_PRIMARY = "#1F3F6E"     # Primary Blue
BRAND_ACCENT = "#D8232A"      # Accent Red
BRAND_DARK = "#1E1E1E"        # Dark Text
BRAND_MUTED = "#6B7280"       # Muted Gray
BRAND_LIGHT = "#F4F6F8"       # Light Background
BRAND_WHITE = "#FFFFFF"       # Panel White
BRAND_BORDER = "#E5E7EB"      # Border Gray
BRAND_HOVER = "#2A528F"       # Hover Blue
BRAND_SUCCESS = "#2A528F"     # Use blue-toned confirmation instead of green
BRAND_TEXT = "#1E1E1E"

# ---------------------------------------------------------------------------
# Core Extraction Logic
# ---------------------------------------------------------------------------

def should_ignore(line: str) -> bool:
    """Ignore headers, footers and page numbers that might break multiline descriptions."""
    ignore_patterns = [
        "CERAGON NETWORKS LTD",
        "Page ",
        "Commercial Invoice No.",
        "Bill To:", "Sold To:", "Ship To:",
        "Customer VAT:", "Tel:", "Fax:",
        "Sales Order No.", "Customer P.O. No:", "Project:", "Packing List No.",
        "S.O. Type:", "Shipment Terms:", "Ship Via:", "Credit Terms:", "End User:",
        "Delivery Gross weight:", "Delivery Net weight:",
        "Line PO Model No.", "# Line P/N Net", "# Weight Origin",
        "Shipment Declaration", "Sub Total:", "V.A.T:", "Total Amount", "For Customs",
        "Remarks", "Identifier =", "Covered under Internet Protocol",
        "Company Registration:", "Self-Declaration:", "Manufactured by",
        "Wireless Radio Link", "V.A.T. File No:"
    ]
    for pattern in ignore_patterns:
        if pattern.lower() in line.lower():
            return True
    if re.match(r'^[-_]+$', line):
        return True
    return False

def parse_ceragon_invoice(pdf_path: str):
    invoice_no = ""
    doc_date_raw = ""
    currency = "USD"
    items = {}
    last_line_no = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Extract Invoice Number
                if not invoice_no and "Commercial Invoice No." in line:
                    match = re.search(r"Commercial Invoice No\.\s+(\S+)", line)
                    if match:
                        invoice_no = match.group(1)
                
                # Extract Date 
                date_match = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{4})", line)
                if date_match and not doc_date_raw:
                    doc_date_raw = date_match.group(1)
                    
                # Extract Currency
                curr_match = re.search(r"Unit Price\s*\[([A-Z]{3})\]", line)
                if curr_match:
                    currency = curr_match.group(1)
                elif "[USD]" in line and "Unit Price" in line:
                    currency = "USD"
                elif "Total Amount [" in line:
                    c_m = re.search(r"Total Amount \[([A-Z]{3})\]", line)
                    if c_m:
                        currency = c_m.group(1)
                
                # Try to extract a line item row
                # Pattern A (Airtel): Line# PO Model Desc... KG Weight CoO Qty UnitPrice Total  (10 groups)
                item_start_match = re.match(r"^(\d+\.\d+)\s+(\S+)\s+(\S+)\s+(.+?)\s+([A-Z]{2,3})\s+([0-9.,]+)\s+([A-Z]{2})\s+([0-9.,]+)\s+([0-9.,]+)\s+([0-9.,]+)$", line)
                if item_start_match:
                    line_no = item_start_match.group(1)
                    part_no = item_start_match.group(2)
                    desc = item_start_match.group(4).strip()
                    coo = item_start_match.group(7).strip()
                    qty = item_start_match.group(8).replace(',', '')
                    unit_price = item_start_match.group(9).replace(',', '')
                else:
                    # Pattern B (Hexacom): Line# PO Model Desc... CoO Qty UnitPrice Total  (8 groups, no KG weight)
                    item_start_match = re.match(r"^(\d+\.\d+)\s+(\S+)\s+(\S+)\s+(.+?)\s+([A-Z]{2})\s+([0-9.,]+)\s+([0-9.,]+)\s+([0-9.,]+)$", line)
                    if item_start_match:
                        line_no = item_start_match.group(1)
                        part_no = item_start_match.group(2)
                        desc = item_start_match.group(4).strip()
                        coo = item_start_match.group(5).strip()
                        qty = item_start_match.group(6).replace(',', '')
                        unit_price = item_start_match.group(7).replace(',', '')
                    else:
                        item_start_match = None
                        
                if item_start_match:
                    items[line_no] = {
                        "part_no": part_no,
                        "desc": desc,
                        "coo": coo,
                        "qty": qty,
                        "unit_price": unit_price
                    }
                    last_line_no = line_no
                elif last_line_no and not should_ignore(line):
                    # Multi-line description logic
                    if not re.search(r"^\d+\.\d+", line) and len(line) > 2:
                        items[last_line_no]["desc"] += " " + line.strip()

    # Format date
    doc_date_formatted = doc_date_raw
    if doc_date_raw:
        try:
            parsed_date = datetime.datetime.strptime(doc_date_raw, "%d-%b-%Y")
            doc_date_formatted = parsed_date.strftime("%d-%m-%Y")
        except:
            pass

    items_list = list(items.values())
    return invoice_no, doc_date_formatted, currency, items_list, "Ceragon"

def parse_ciena_invoice(pdf_path: str):
    invoice_no = ""
    doc_date_formatted = ""
    currency = "USD"
    items_list = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            words = page.extract_words()
            text = page.extract_text() or ""
            lines = text.split("\n")
            
            if not invoice_no:
                inv_match = re.search(r"COMMERCIAL\s+INVOICE\s+NO\.\s*(\S+)", text, re.IGNORECASE)
                if inv_match:
                    invoice_no = inv_match.group(1)
                else:
                    fallback_match = re.search(r"Invoice\s*#:\s*(?:[^\n]*\n)?\s*(\S+)", text, re.IGNORECASE)
                    if fallback_match:
                        invoice_no = fallback_match.group(1)

            date_match = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{4})", text)
            if date_match and not doc_date_formatted:
                doc_date_raw = date_match.group(1)
                try:
                    parsed_date = datetime.datetime.strptime(doc_date_raw, "%d-%b-%Y")
                    doc_date_formatted = parsed_date.strftime("%d-%m-%Y")
                except ValueError:
                    doc_date_formatted = doc_date_raw
                    
            curr_match = re.search(r"Currency:\s*(\S+)", text, re.IGNORECASE)
            if curr_match:
                currency = curr_match.group(1)

            page_items = []
            for line in lines:
                match = re.match(r"^(\d+)\s+(\d+)\s+([A-Za-z]{2,3})\s+(\S+)\s+(\d+)\s+([A-Z]{2})\s+([0-9.,]+)\s+([0-9.,]+)$", line)
                if match:
                    qty = match.group(2)
                    uom = match.group(3)
                    part_no = match.group(4)
                    coo = match.group(6)
                    unit_val = match.group(7).replace(',', '')
                    page_items.append({
                        "part_no": part_no,
                        "desc": part_no, # Will refine description if available, else part_no
                        "coo": coo,
                        "qty": qty,
                        "uom": uom,
                        "unit_price": unit_val
                    })
            items_list.extend(page_items)
            
    return invoice_no, doc_date_formatted, currency, items_list, "Ciena"

def parse_eci_invoice(pdf_path: str):
    invoice_no = ""
    doc_date_formatted = ""
    currency = "USD"
    coo = ""
    items = []

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        
        inv_match = re.search(r"Invoice\s*/?\s*Delivery\s+No:\s*(\S+)", full_text, re.IGNORECASE)
        if inv_match:
            invoice_no = inv_match.group(1)
        
        date_match = re.search(r"Date:\s*(\S+)", full_text, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1)
            for fmt in ("%d-%b-%y", "%d-%b-%Y"):
                try:
                    parsed_date = datetime.datetime.strptime(raw_date, fmt)
                    doc_date_formatted = parsed_date.strftime("%d-%m-%Y")
                    break
                except ValueError:
                    continue
            if not doc_date_formatted:
                doc_date_formatted = raw_date
        
        curr_match = re.search(r"Currency:\s*(\S+)", full_text, re.IGNORECASE)
        if curr_match:
            currency = curr_match.group(1)
        
        coo_match = re.search(r"COO:\s*(\S+)", full_text, re.IGNORECASE)
        if coo_match:
            coo = coo_match.group(1).upper()
        
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")
            
            header_idx = None
            for idx, line in enumerate(lines):
                if re.search(r"Item\s+Code", line, re.IGNORECASE):
                    header_idx = idx
                    break
            
            if header_idx is None:
                continue
            
            for line in lines[header_idx + 1:]:
                line = line.strip()
                if not line:
                    continue
                if re.search(r"(SUBTOTAL|GRAND TOTAL|NO RETURNS|Signature|Prepaid|ECI Telecom)", line, re.IGNORECASE):
                    break
                
                row_match = re.match(
                    r"^(\d+)\s+(.+?)\s+([A-Z0-9][\w-]*)\s+([0-9,]+\.\d+)\s+(\d+)\s+(\d+)\s+([A-Za-z]{2,3})\s+([0-9,]+\.\d+)$", line
                )
                if row_match:
                    product_name = row_match.group(2).strip()
                    item_code = row_match.group(3).strip()
                    unit_price = row_match.group(4).replace(",", "")
                    shipped_qty = row_match.group(6) 
                    uom = row_match.group(7)
                    
                    items.append({
                        "part_no": item_code,
                        "desc": product_name,
                        "qty": shipped_qty,
                        "uom": uom,
                        "unit_price": unit_price,
                        "coo": coo
                    })
                    
    return invoice_no, doc_date_formatted, currency, items, "ECI"

def parse_bharti_invoice(pdf_path: str):
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0].extract_text() or ""
        first_page_upper = first_page.upper()
        
        if "CERAGON" in first_page_upper:
            return parse_ceragon_invoice(pdf_path)
        elif "CIENA" in first_page_upper:
            return parse_ciena_invoice(pdf_path)
        elif "ECI" in first_page_upper or "ECI TELECOM" in first_page_upper:
            return parse_eci_invoice(pdf_path)
        else:
            raise ValueError("Could not detect Bharti format (Not Ceragon, Ciena, or ECI). Please ensure this is a valid Bharti Airtel / Hexacom invoice.")

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------
class BhartiExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bharti Invoice Extractor")
        try:
            self.root.state('zoomed')
        except Exception:
            self.root.geometry("1100x700")
        self.root.configure(bg=BRAND_LIGHT)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=BRAND_PRIMARY, foreground=BRAND_WHITE)
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=25, background=BRAND_WHITE, fieldbackground=BRAND_WHITE)
        
        self.extracted_items = []
        
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BRAND_WHITE, height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        try:
            logo_path = resource_path("logo.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                aspect_ratio = img.width / img.height
                target_height = 20
                target_width = int(target_height * aspect_ratio)
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(header, image=self.logo_img, bg=BRAND_WHITE).pack(side=tk.LEFT, padx=20, pady=10)
        except Exception as e:
            logger.warning(f"Logo not loaded: {e}")

        title_lbl = tk.Label(
            header,
            text="BHARTI INVOICE EXTRACTOR",
            font=("Segoe UI", 14, "bold"),
            bg=BRAND_WHITE,
            fg=BRAND_DARK
        )
        title_lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        main_content = tk.Frame(self.root, bg=BRAND_LIGHT, padx=20, pady=20)
        main_content.pack(fill=tk.BOTH, expand=True)

        controls = tk.Frame(main_content, bg=BRAND_LIGHT)
        controls.pack(fill=tk.X, pady=(0, 15))

        tk.Label(controls, text="Select PDF:", bg=BRAND_LIGHT, font=("Segoe UI", 10, "bold"), fg=BRAND_TEXT).pack(side=tk.LEFT)
        self.entry_path = tk.Entry(controls, font=("Segoe UI", 10), width=60, bg=BRAND_WHITE, highlightbackground=BRAND_BORDER, highlightcolor=BRAND_PRIMARY, highlightthickness=1)
        self.entry_path.pack(side=tk.LEFT, padx=10, ipady=3)

        tk.Button(controls, text="Browse...", font=("Segoe UI", 9), command=self._browse_file, bg=BRAND_WHITE, fg=BRAND_PRIMARY, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=5)
        tk.Button(controls, text="🚀 Extract Data", font=("Segoe UI", 9, "bold"), bg=BRAND_PRIMARY, fg=BRAND_WHITE, activebackground=BRAND_HOVER, activeforeground=BRAND_WHITE, relief=tk.FLAT, command=self._extract).pack(side=tk.LEFT, padx=10)
        tk.Button(controls, text="✖ Clear All", font=("Segoe UI", 9), command=self._clear, bg=BRAND_WHITE, fg=BRAND_DARK, relief=tk.SOLID, bd=1).pack(side=tk.LEFT)
        self.btn_export = tk.Button(controls, text="📥 Export Data", font=("Segoe UI", 9, "bold"), bg=BRAND_PRIMARY, fg=BRAND_WHITE, activebackground=BRAND_HOVER, activeforeground=BRAND_WHITE, relief=tk.FLAT, state=tk.DISABLED, command=self._export)
        self.btn_export.pack(side=tk.RIGHT)

        columns = ("Invoice No", "Invoice Date", "Model No", "Description", "Qty", "UOM", "Currency", "Unit Price", "COO")
        self.tree = ttk.Treeview(main_content, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = 250 if col == "Description" else (120 if col in ("Invoice No", "Model No") else 80)
            self.tree.column(col, width=width, anchor=tk.W if col in ("Description", "Model No", "Invoice No") else tk.CENTER)

        scrollbar = ttk.Scrollbar(main_content, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        footer = tk.Frame(self.root, bg=BRAND_LIGHT, height=30)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(footer, text="Nagarkot Forwarders Pvt. Ltd. ©", bg=BRAND_LIGHT, fg=BRAND_MUTED, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=10, pady=5)
        
        self.lbl_status = tk.Label(footer, text="Ready", bg=BRAND_LIGHT, fg=BRAND_MUTED, font=("Segoe UI", 8))
        self.lbl_status.pack(side=tk.RIGHT, padx=10, pady=5)

    def _browse_file(self):
        filepaths = filedialog.askopenfilenames(
            title="Select Bharti PDF Invoices",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if filepaths:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, " | ".join(filepaths))

    def _clear(self):
        self.entry_path.delete(0, tk.END)
        self.tree.delete(*self.tree.get_children())
        self.extracted_items = []
        self.btn_export.config(state=tk.DISABLED)
        self.lbl_status.config(text="Ready", fg=BRAND_MUTED)

    def _extract(self):
        filepaths_raw = self.entry_path.get().strip()
        if not filepaths_raw:
            messagebox.showerror("Error", "Please select at least one valid PDF file.")
            return

        filepaths = [fp.strip() for fp in filepaths_raw.split("|") if fp.strip() and os.path.exists(fp.strip())]
        if not filepaths:
            messagebox.showerror("Error", "No valid files found. Please re-select.")
            return

        self.tree.delete(*self.tree.get_children())
        self.lbl_status.config(text=f"Extracting {len(filepaths)} files... Please wait.", fg=BRAND_MUTED)
        self.root.update()

        self.extracted_items = []
        errors = []
        success_count = 0

        for filepath in filepaths:
            try:
                inv_no, doc_date, currency, items, format_detected = parse_bharti_invoice(filepath)
                
                if not items:
                    raise ValueError(f"No items could be extracted using the {format_detected} format.")
                
                for item in items:
                    item['Invoice No'] = inv_no
                    item['Invoice Date'] = doc_date
                    item['Currency'] = currency
                    self.extracted_items.append(item)
                    
                    self.tree.insert("", tk.END, values=(
                        inv_no,
                        doc_date,
                        item.get("part_no", ""),
                        item.get("desc", ""),
                        item.get("qty", ""),
                        item.get("uom", "PCS"),
                        currency,
                        item.get("unit_price", ""),
                        item.get("coo", "")
                    ))
                success_count += 1
            except Exception as e:
                filename = os.path.basename(filepath)
                logger.exception(f"Extraction failed for {filename}")
                errors.append(f"{filename}: {e}")

        if success_count > 0:
            self.btn_export.config(state=tk.NORMAL)
            status_text = f"Successfully extracted {len(self.extracted_items)} items from {success_count} files."
            if errors:
                status_text += f" ({len(errors)} files failed)."
                messagebox.showwarning("Partial Success", "Some files failed to process:\n" + "\n".join(errors))
            self.lbl_status.config(text=status_text, fg=BRAND_SUCCESS)
        else:
            messagebox.showerror("Error", "Failed to extract data from any of the selected files:\n" + "\n".join(errors))
            self.lbl_status.config(text="Extraction failed completely.", fg=BRAND_ACCENT)

    def _export(self):
        if not self.extracted_items:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv"), ("Excel File", "*.xlsx")],
            title="Save Extracted Data"
        )
        if not file_path:
            return

        try:
            export_data = []

            for item in self.extracted_items:
                export_data.append({
                    "Invoice No": item.get("Invoice No", ""),
                    "Invoice Date": item.get("Invoice Date", ""),
                    "Model": item.get("part_no", ""),
                    "Quantity": item.get("qty", ""),
                    "Unit Price": item.get("unit_price", ""),
                    "UOM": item.get("uom", "PCS"),
                    "Currency": item.get("Currency", "USD"),
                    "Product Desc": item.get("desc", ""),
                    "Country of Origin": item.get("coo", "")
                })

            df_export = pd.DataFrame(export_data)

            if file_path.endswith('.csv'):
                df_export.to_csv(file_path, index=False)
            else:
                df_export.to_excel(file_path, index=False)

            messagebox.showinfo("Success", f"Data exported to:\n{file_path}")
            self.lbl_status.config(text="Data exported successfully.", fg=BRAND_SUCCESS)

        except Exception as e:
            logger.exception("Export error")
            messagebox.showerror("Error", f"Failed to export data:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BhartiExtractorApp(root)
    root.mainloop()
