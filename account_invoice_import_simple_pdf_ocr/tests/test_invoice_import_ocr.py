# -*- coding: utf-8 -*-
# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>

import base64
import os
from odoo.tests.common import TransactionCase, tagged
from odoo.modules.module import get_module_resource

@tagged('post_install', '-at_install')
class TestInvoiceImportOcr(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup test environment
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Create a test partner with specific PDF keywords
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Vendor OCR',
            'simple_pdf_keyword': 'TEST INVOICE|OCRTESTING',
        })

        # Load test files from the module test_files directory
        cls.test_files_path = get_module_resource(
            'account_invoice_import_simple_pdf_ocr', 'tests', 'test_files')

        # We'll check if directory exists - if not, tests will be skipped
        cls.has_test_files = cls.test_files_path and os.path.isdir(cls.test_files_path)

    def _load_file(self, filename):
        """Helper to load a test file from the test_files directory"""
        file_path = os.path.join(self.test_files_path, filename)
        if not os.path.exists(file_path):
            return False

        with open(file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data)

    def test_01_scanned_invoice_ocr(self):
        """Test OCR extraction on a scanned invoice PDF (image-based)"""
        if not self.has_test_files:
            self.skipTest('Test files directory not found')

        # Load sample scanned invoice
        file_data = self._load_file('sample_scanned_invoice.pdf')
        if not file_data:
            self.skipTest('Sample scanned invoice file not found')

        # Initialize test info dict
        test_info = {'test_mode': True}
        wizard = self.env['account.invoice.import'].create({})

        # Update test_info with necessary keys
        wizard._simple_pdf_update_test_info(test_info)

        # Test OCR extraction
        decoded_data = base64.b64decode(file_data)
        text_dict = wizard.simple_pdf_text_extraction(decoded_data, test_info)

        # Check if OCR returned results
        self.assertTrue(text_dict, "OCR extraction failed to return text")
        self.assertTrue(text_dict.get('all'), "OCR extraction did not return 'all' text")
        self.assertTrue(text_dict.get('first'), "OCR extraction did not return 'first' text")

        # Check if extraction method is Tesseract
        self.assertEqual(test_info.get('text_extraction'), 'Tesseract',
                         "OCR extraction was not performed with Tesseract")

    def test_02_fallback_parse_pdf(self):
        """Test fallback method for PDF parsing with OCR"""
        if not self.has_test_files:
            self.skipTest('Test files directory not found')

        # Load sample scanned invoice
        file_data = self._load_file('sample_scanned_invoice.pdf')
        if not file_data:
            self.skipTest('Sample scanned invoice file not found')

        # Test the fallback method
        wizard = self.env['account.invoice.import'].create({})
        company = self.env.company

        # Call the fallback method
        decoded_data = base64.b64decode(file_data)
        result = wizard.fallback_parse_pdf_invoice(decoded_data, company)

        # We don't need to check exact result content since it depends on the file,
        # but we should check that it returns something
        self.assertIsInstance(result, dict, "fallback_parse_pdf_invoice should return a dict")

    def test_03_specific_tool_selection(self):
        """Test specific tool selection for PDF text extraction"""
        if not self.has_test_files:
            self.skipTest('Test files directory not found')

        # Load sample scanned invoice
        file_data = self._load_file('sample_scanned_invoice.pdf')
        if not file_data:
            self.skipTest('Sample scanned invoice file not found')

        # Set parameter to use tesseract specifically
        self.env['ir.config_parameter'].sudo().set_param('invoice_import_simple_pdf.pdf2txt', 'tesseract')

        # Initialize wizard and test info
        wizard = self.env['account.invoice.import'].create({})
        test_info = {'test_mode': True}
        wizard._simple_pdf_update_test_info(test_info)

        # Decode file data
        decoded_data = base64.b64decode(file_data)

        # Test extraction with specific tool parameter
        text_dict = wizard.simple_pdf_text_extraction(decoded_data, test_info)

        # Verify results
        self.assertTrue(text_dict, "Text extraction failed with specific tool")
        self.assertEqual(test_info.get('text_extraction'), 'Tesseract',
                        "Text extraction was not performed with Tesseract as specified")
