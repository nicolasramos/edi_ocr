# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
import logging
import os
from tempfile import NamedTemporaryFile

from odoo import _, api, models
from odoo.exceptions import UserError

# Set Tesseract data directory - can be configured differently depending on OS
# TESSDATA_PREFIX = "/usr/share/tesseract-ocr/5/tessdata" # This line is removed
# os.environ["TESSDATA_PREFIX"] = TESSDATA_PREFIX # This line is removed

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
try:
    from paddleocr import PaddleOCR
except ImportError:
    logger.debug("Cannot import paddleocr")


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
        # Get TESSDATA_PREFIX from system parameters
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        tessdata_prefix = IrConfigParameter.get_param(
            "account_invoice_import_simple_pdf_ocr.tessdata_prefix",
            "/usr/share/tesseract-ocr/5/tessdata"  # Default value
        )
        original_tessdata_prefix = os.environ.get("TESSDATA_PREFIX")
        os.environ["TESSDATA_PREFIX"] = tessdata_prefix
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
                logger.info("Text extraction performed with Tesseract OCR using TESSDATA_PREFIX: %s", tessdata_prefix)
                test_info["text_extraction"] = "Tesseract"

                # Process text for space removal
                res["all_no_space"] = regex.sub(
                    "%s+" % test_info["space_pattern"], "", res["all"]
                )
                res["first_no_space"] = regex.sub(
                    "%s+" % test_info["space_pattern"], "", res["first"]
                )
        except Exception as e:
            logger.warning("Text extraction with Tesseract failed. Error: %s. Using TESSDATA_PREFIX: %s", e, tessdata_prefix)
        finally:
            # Restore original TESSDATA_PREFIX if it was set, otherwise unset it
            if original_tessdata_prefix is not None:
                os.environ["TESSDATA_PREFIX"] = original_tessdata_prefix
            elif "TESSDATA_PREFIX" in os.environ:
                del os.environ["TESSDATA_PREFIX"]
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
    def _simple_pdf_text_extraction_paddle(self, fileobj, test_info):
        """Extract text from PDF using PaddleOCR"""
        res = False
        try:
            # Get language from config
            IrConfigParameter = self.env["ir.config_parameter"].sudo()
            lang = IrConfigParameter.get_param(
                "account_invoice_import_simple_pdf_ocr.paddle_lang", "en"
            )
            
            # Initialize PaddleOCR
            # use_textline_orientation=True helps with rotated text
            # show_log=False to reduce noise
            ocr = PaddleOCR(use_textline_orientation=True, lang=lang, show_log=False)
            
            # Convert PDF to images
            images = convert_from_path(fileobj.name)
            if not images:
                logger.warning("No images extracted from PDF")
                return False

            output = []
            for i, img in enumerate(images):
                # PaddleOCR expects array or path. We can pass numpy array from PIL image.
                import numpy as np
                img_array = np.array(img)
                
                result = ocr.ocr(img_array, cls=True)
                # Result structure: [[[[x,y],..], ("text", conf)], ...]
                # We need to concatenate text lines.
                page_text = ""
                if result and result[0]:
                    # Paddle returns line by line.
                    lines = [line[1][0] for line in result[0]]
                    page_text = "\n".join(lines)
                
                if page_text:
                    output.append(page_text)
                else:
                     logger.warning("No text extracted from page %s using PaddleOCR", i+1)

            if output:
                res = {
                    "all": "\n".join(output),
                    "first": output[0] if output else "",
                }
                logger.info("Text extraction performed with PaddleOCR (lang=%s)", lang)
                test_info["text_extraction"] = "PaddleOCR"

                # Process text for space removal
                res["all_no_space"] = regex.sub(
                    "%s+" % test_info["space_pattern"], "", res["all"]
                )
                res["first_no_space"] = regex.sub(
                    "%s+" % test_info["space_pattern"], "", res["first"]
                )
        except Exception as e:
            logger.warning("Text extraction with PaddleOCR failed. Error: %s", e)
        
        return res

    @api.model
    def _simple_pdf_text_extraction_specific_tool(
        self, specific_tool, fileobj, test_info
    ):
        """Handle specific tool selection for text extraction"""
        res = False
        if specific_tool == "tesseract":
            res = self._simple_pdf_text_extraction_tesseract(fileobj, test_info)
        elif specific_tool == "paddle":
            res = self._simple_pdf_text_extraction_paddle(fileobj, test_info)
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
        """Override to include tesseract and paddle in the text extraction chain"""
        
        # Check if Paddle is selected as the specific tool (from system param)
        specific_tool = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account_invoice_import_simple_pdf_ocr.ocr_engine")
        )
        
        # If it is set to paddle, try it first
        if specific_tool == "paddle":
             try:
                 # We need to write to temp file first because simple_pdf logic often expects file path
                 # Although fallback_parse method does it too.
                 with NamedTemporaryFile("wb", prefix="odoo-simple-pdf-", suffix=".pdf") as fileobj:
                    fileobj.write(file_data)
                    fileobj.seek(0)
                    res = self._simple_pdf_text_extraction_paddle(fileobj, test_info)
                    if res:
                        return res
             except Exception:
                 pass # Fallback to others

        # Fallback to parent logic (which calls specific_tool if set via invoice_import_simple_pdf.pdf2txt)
        # Note: parent uses 'invoice_import_simple_pdf.pdf2txt' param. We added 'account_invoice_import_simple_pdf_ocr.ocr_engine'.
        # We should make sure we don't conflict. 
        
        # First try with parent implementation
        res = super().simple_pdf_text_extraction(file_data, test_info)

        # If text extraction failed with standard methods, try with Tesseract (legacy logic we added before)
        if not res or (res and not res.get("all")):
             # ... tesseract logic ... 
             pass
             
        return res

    @api.model
    def _prepare_line_vals_1line(self, parsed_inv, import_config, vals, partner):
        res = super()._prepare_line_vals_1line(parsed_inv, import_config, vals, partner)
        if parsed_inv.get("analytic_distribution"):
            # Update the last added line
            if vals.get("invoice_line_ids"):
                last_cmd = vals["invoice_line_ids"][-1]
                # last_cmd is (0, 0, {values})
                if last_cmd[0] == 0:
                     last_cmd[2]["analytic_distribution"] = parsed_inv["analytic_distribution"]
        return res

