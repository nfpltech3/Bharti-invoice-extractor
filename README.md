# Bharti Invoice Extractor

This tool bridges the gap between raw Bharti Airtel and Bharti Hexacom supplier invoices (PDFs) and the Nagarkot Checklist Tool by parsing the documents into our **Standard Data Contract**.

## How It Works

### Inputs & Allowed Formats
- **Input File Type:** PDF Documents (`.pdf`)
- **Note:** This tool uses `pdfplumber` to extract text line-by-line from Commercial Invoices.

### Extraction Logic & Auto-Detection
Because PDFs lack structured tables, the tool scans the text to identify the specific invoice layout. It automatically detects three known Bharti formats:
- **Ceragon:** Detects the word "CERAGON" on the first page. Supports both Airtel and Hexacom formats. Extracts using Line Number / PO / Model / Description / COO / Qty / UnitPrice logic.
- **Ciena:** Detects the word "CIENA" on the first page. Extracts using Qty / UOM / Part# / HTS / COO / UnitPrice logic.
- **ECI Telecom:** Detects the word "ECI" on the first page. Extracts using ItemCode / UnitPrice / OrderedQty / ShippedQty / UOM logic.

*Note: It will automatically apply the correct extraction logic based on the detected format.*

### Outputs
- **Output File Type:** Standardized CSV (`.csv`) or Excel (`.xlsx`).
- **Checklist Tool Integration:** The resulting CSV file can be directly uploaded into the **Main Checklist Generator Tool**.
- ⚠️ **Important Manual Checks:** While the tool extracts the text exactly, you must ensure that manual adjustments required by Customs are done in the Main Checklist Tool (e.g., verifying `SQC Unit` conversions, missing country of origin, etc.).

---

## Installation

### Clone
```bash
git clone https://github.com/nfpltech3/Bharti-invoice-extractor.git
cd Bharti-invoice-extractor
```

---

## Python Setup (MANDATORY)

⚠️ **IMPORTANT:** You must use a virtual environment.

1. Create virtual environment
```bash
python -m venv venv
```

2. Activate (REQUIRED)

Windows:
```cmd
venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Application

Once the virtual environment is activated, run:
```bash
python Bharti_Extractor.py
```

## Compiling to `.exe`

If you need to generate a standalone Windows executable:
```bash
venv\Scripts\pyinstaller.exe Bharti_Extractor.spec
```
The resulting `Bharti_Extractor.exe` will be located in the `dist/` directory.
