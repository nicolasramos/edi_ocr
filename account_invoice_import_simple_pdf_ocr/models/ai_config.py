# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
import threading

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ollama_endpoint = fields.Char(
        string="Ollama Endpoint",
        config_parameter="account_invoice_import_simple_pdf_ocr.ollama_endpoint",
        default="http://ollama:11434/api/generate",
        help="URL of the Ollama API, e.g. http://ollama:11434/api/generate or http://localhost:11434/api/generate"
    )
    ollama_model = fields.Char(
        string="Ollama Model",
        config_parameter="account_invoice_import_simple_pdf_ocr.ollama_model",
        default="gemma:2b",
        help="Tag of the model to use, e.g. gemma:2b, phi3, llama3.2"
    )
    ollama_prompt = fields.Text(
        string="Ollama System Prompt",
        default="You are a regex expert...",
        help="Prompt sent to the AI. Use {text} placeholder for the invoice content.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        res["ollama_prompt"] = self.env["ir.config_parameter"].sudo().get_param(
            "account_invoice_import_simple_pdf_ocr.ollama_prompt",
            default="You are a regex expert..."
        )
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "account_invoice_import_simple_pdf_ocr.ollama_prompt", 
            self.ollama_prompt
        )

    ocr_engine = fields.Selection(
        [("tesseract", "Tesseract"), ("paddle", "PaddleOCR")],
        string="OCR Engine",
        config_parameter="account_invoice_import_simple_pdf_ocr.ocr_engine",
        default="paddle",
        help="Select the OCR engine to use. PaddleOCR is recommended for CPU performance."
    )
    paddle_lang = fields.Char(
        string="PaddleOCR Language",
        config_parameter="account_invoice_import_simple_pdf_ocr.paddle_lang",
        default="en",
        help="Language code for PaddleOCR, e.g. 'en', 'es', 'fr'"
    )

    def action_download_ollama_model(self):
        self.ensure_one()
        endpoint = self.ollama_endpoint
        model = self.ollama_model
        
        if not endpoint or not model:
            raise UserError(_("Please configure Ollama Endpoint and Model first."))
            
        # Adjust endpoint to point to /api/pull
        # The stored endpoint is usually .../api/generate. We need root or just replace path.
        if "/api/generate" in endpoint:
            pull_url = endpoint.replace("/api/generate", "/api/pull")
        else:
            # Fallback if user entered root url
            pull_url = endpoint.rstrip("/") + "/api/pull"
        
        def run_pull():
            try:
                _logger.info("Starting background model pull for %s", model)
                # timeout=None means wait forever (or until TCP closes)
                # Since Ollama might take minutes, this is safer in a thread.
                response = requests.post(pull_url, json={"name": model, "stream": False}, timeout=None)
                response.raise_for_status()
                _logger.info("Model pull finished successfully for %s", model)
            except Exception as e:
                _logger.error("Background model pull failed for %s: %s", model, e)
        
        thread = threading.Thread(target=run_pull)
        thread.start()
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Download Started"),
                "message": _("The model download has started in the background. Please wait a few minutes and check logs for completion."),
                "type": "info",
                "sticky": False,
            }
        }
