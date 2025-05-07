# Test files for OCR testing

Place your test PDF files in this directory for OCR testing.

Recommended test files:
1. `sample_scanned_invoice.pdf` - A scanned invoice with text in images
2. `sample_text_invoice.pdf` - A PDF with selectable text
3. `sample_mixed_invoice.pdf` - A PDF with both selectable text and images

These files are used by the automated tests to verify OCR functionality.
When running the tests, if these files don't exist, the relevant tests will be skipped.

## Test file requirements

For proper testing, scan some sample invoices with the following characteristics:
- Preferably in Spanish language (for tesseract-ocr-spa)
- Include at least one page
- Include the text "TEST INVOICE" or "OCRTESTING" for partner matching tests
- Include fields like dates, amounts, and tax information
