# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
from odoo import models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_simple_pdf_ai_extraction(self):
        self.ensure_one()
        return {
            "name": _("Detect Rules with AI"),
            "type": "ir.actions.act_window",
            "res_model": "ai.extraction.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                # Pre-fill file if we have one in the context or fields?
                # The wizard needs a file. The partner has 'simple_pdf_test_file'.
                # Let's pass it if available.
                "default_file_content": self.simple_pdf_test_file,
                "default_filename": self.simple_pdf_test_filename,
            },
        }
