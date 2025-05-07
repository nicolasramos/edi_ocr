# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
{
    "name": "Account Invoice Import Simple PDF OCR",
    "summary": """
        Import simple PDF vendor bills with OCR
    """,
    "description": """
        This module extends the account_invoice_import_simple_pdf module
        by adding OCR capabilities using Tesseract.
        It allows extracting text from PDF files that contain images.
    """,
    "author": "Nicolás Ramos",
    "website": "https://nicolasramos.es",
    "license": "OPL-1",  # "AGPL-3" "LGPL-3" "OPL-1" "Other OSI approved licence" "Other proprietary"
    "category": "Accounting",
    "version": "16.0.1.0.0",
    "depends": [
        "account_invoice_import_simple_pdf",
    ],
    "external_dependencies": {
        "python": [
            "pdf2image",
            "pytesseract",
            "regex",
        ],
        "deb": ["tesseract-ocr-spa", "poppler-utils"],
    },
    "data": [
        "data/ir_config_parameter_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Add any JS/CSS assets if needed
        ],
    },
    "demo": [],
    "images": [],
    "maintainers": ["nicolasramos"],
    "installable": True,
    "application": False,
}
