# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
import logging
import os
from tempfile import NamedTemporaryFile

from odoo import _, api, models
from odoo.exceptions import UserError

# Set Tesseract data directory - can be configured differently depending on OS
TESSDATA_PREFIX = "/usr/share/tesseract-ocr/4.00/tessdata"
os.environ["TESSDATA_PREFIX"] = TESSDATA_PREFIX

logger = logging.getLogger(__name__)

try:
    import regex
except ImportError:
    logger.debug("Cannot import regex")
try:
    import pytesseract
    from PIL import Image
except ImportError:
    logger.debug("Cannot import pytesseract or PIL")
try:
    from pdf2image import convert_from_path
except ImportError:
    logger.debug("Cannot import pdf2image")


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    @api.model
    def fallback_parse_pdf_invoice(self, file_data, company=False):
        """This method should be inherited by additional modules with
        the same logic as the account_bank_statement_import_* modules"""
        res = super().fallback_parse_pdf_invoice(file_data)
        if not res:
            # Create test_info dictionary for OCR processing
            test_info = {"test_mode": False}
            self._simple_pdf_update_test_info(test_info)

            # Create temporary file
            with NamedTemporaryFile("wb", prefix="odoo-simple-pdf-", suffix=".pdf") as fileobj:
                fileobj.write(file_data)
                fileobj.seek(0)

                # Try OCR extraction
                try:
                    raw_text_dict = self._simple_pdf_text_extraction_tesseract(fileobj, test_info)
                    if raw_text_dict:
                        # Process extracted text similar to simple_pdf_parse_invoice
                        partner_id = self.simple_pdf_match_partner(raw_text_dict["all_no_space"])
                        if not partner_id:
                            return {"chatter_msg": ["Simple PDF OCR Import: could not find Vendor."]}

                        # Continue with simple_pdf module's logic
                        return self.simple_pdf_parse_invoice(file_data, test_info)
                except Exception as e:
                    logger.error("OCR text extraction failed: %s", e)
                    return {"chatter_msg": [_("OCR text extraction failed. Error: %s") % str(e)]}

        return res

    @api.model
    def _simple_pdf_text_extraction_tesseract(self, fileobj, test_info):
        """Extract text from PDF using Tesseract OCR"""
        res = False
        try:
            # Convert PDF to images
            images = convert_from_path(fileobj.name)
            if not images:
                logger.warning("No images extracted from PDF")
                return False

            # Process each page with OCR
            output = []
            for i, img in enumerate(images):
                text = pytesseract.image_to_string(img, lang='spa')
                if text:
                    output.append(text)
                else:
                    logger.warning("No text extracted from page %s", i+1)

            # If we have extracted text, return it
            if output:
                res = {
                    "all": "\n".join(output),
                    "first": output[0] if output else "",
                }
                logger.info("Text extraction performed with Tesseract OCR")
                test_info["text_extraction"] = "Tesseract"

                # Process text for space removal
                res["all_no_space"] = regex.sub(
                    "%s+" % test_info["space_pattern"], "", res["all"]
                )
                res["first_no_space"] = regex.sub(
                    "%s+" % test_info["space_pattern"], "", res["first"]
                )
        except Exception as e:
            logger.warning("Text extraction with Tesseract failed. Error: %s", e)

        return res

    @api.model
    def _simple_pdf_text_extraction_specific_tool(
        self, specific_tool, fileobj, test_info
    ):
        """Handle specific tool selection for text extraction"""
        res = False
        if specific_tool == "tesseract":
            res = self._simple_pdf_text_extraction_tesseract(fileobj, test_info)
        else:
            # Call parent implementation for other tools
            return super()._simple_pdf_text_extraction_specific_tool(
                specific_tool, fileobj, test_info
            )

        if not res:
            raise UserError(
                _(
                    "Odoo could not extract the text from the PDF invoice "
                    "with the method %s. Refer to the Odoo server logs for more technical "
                    "information about the cause of the failure."
                )
                % specific_tool
            )
        return res

    @api.model
    def simple_pdf_text_extraction(self, file_data, test_info):
        """Override to include tesseract in the text extraction chain"""
        # First try with parent implementation
        res = super(AccountInvoiceImport, self).simple_pdf_text_extraction(file_data, test_info)

        # If text extraction failed with standard methods, try with Tesseract
        if not res or (res and not res.get("all")):
            with NamedTemporaryFile("wb", prefix="odoo-simple-pdf-", suffix=".pdf") as fileobj:
                fileobj.write(file_data)
                fileobj.seek(0)

                res = self._simple_pdf_text_extraction_tesseract(fileobj, test_info)
                if not res:
                    raise UserError(
                        _(
                            "Odoo could not extract the text from the PDF invoice. "
                            "Refer to the Odoo server logs for more technical information "
                            "about the cause of the failure."
                        )
                    )

        return res
