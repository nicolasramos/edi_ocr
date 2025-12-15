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
    "version": "17.0.1.0.0",
    "depends": [
        "account_invoice_import_simple_pdf",
        "account",
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
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner.xml",
        "wizards/ai_extraction_wizard_views.xml",
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
