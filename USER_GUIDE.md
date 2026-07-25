# Bharti Invoice Extractor - User Guide

## Introduction
The Bharti Invoice Extractor is a desktop application designed to automatically parse Bharti Airtel and Bharti Hexacom PDF invoices (Ceragon, Ciena, and ECI formats).

## How to Use the Tool

### 1. Launch the Application
- If you have the `.exe` file, simply double-click `Bharti_Extractor.exe`.
- If running from source, ensure your virtual environment is active and run `python Bharti_Extractor.py`.

### 2. Select Your Invoice
1. Click the **Browse...** button.
2. Select your Bharti `.pdf` invoice.
3. *Note: The tool will automatically detect if it is a Ceragon, Ciena, or ECI invoice.*

### 3. Extract the Data
1. Click the **🚀 Extract Data** button.
2. The tool will parse the PDF and display the extracted items in the table below.
3. Review the extracted data on the screen to ensure the Model, Description, Quantity, and Unit Price look correct.

### 4. Export to CSV
1. Once you are satisfied with the extraction, click the **📥 Export Data** button.
2. Save the file as a `.csv` (recommended) or `.xlsx`.
3. You can now take this CSV file and upload it directly into the **Nagarkot Checklist Tool**.

## Troubleshooting

- **Error: "Could not detect Bharti format"**: The tool scans the first page for the keywords "CERAGON", "CIENA", or "ECI". If the PDF is scanned as an image (not searchable text) or belongs to a different supplier, the tool cannot extract it.
- **Missing Descriptions**: If multi-line descriptions are getting cut off, it is likely due to page breaks in the PDF interrupting the text flow. Check the CSV output manually.
- **To reset the view**, click the **✖ Clear All** button.
