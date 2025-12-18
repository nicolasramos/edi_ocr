# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
import base64
import json
import logging
import requests
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AIExtractionWizard(models.TransientModel):
    _name = "ai.extraction.wizard"
    _description = "AI Extraction Wizard"

    partner_id = fields.Many2one("res.partner", required=True)
    file_content = fields.Binary(string="File Content", required=True)
    filename = fields.Char(string="Filename")

    def action_detect_rules(self):
        self.ensure_one()
        
        # Helper to map symbols to selection keys
        def map_separator(val, type='date'):
            if not val: 
                return None
            val = val.lower().strip()
            if type == 'date':
                mapping = {'/': 'slash', '-': 'dash', '.': 'dot', ' ': 'space'}
            elif type == 'decimal':
                mapping = {'.': 'dot', ',': 'comma'}
            elif type == 'thousand':
                mapping = {'.': 'dot', ',': 'comma', "'": 'apostrophe', ' ': 'space', 'none': 'none', '': 'none'}
            else:
                return val
            
            # Check if val is in keys (symbol) or values (name)
            if val in mapping:
                return mapping[val]
            # Check if val is already a valid key (e.g. 'slash')
            if val in mapping.values():
                return val
            return None

        # 1. Extract text using existing OCR logic
        file_data = base64.b64decode(self.file_content)
        # We need to provide expected keys in test_info as the base method uses them blindly
        test_info = {
            "test_mode": False,
            "lonely_accents": r"[\u0060\u00B4\u2018\u2019]",
            "space_pattern": r"[\s\u00A0]",
        }
        start_parsing = self.env["account.invoice.import"].simple_pdf_text_extraction(file_data, test_info)
        
        full_text = start_parsing.get("all_no_space", "") or start_parsing.get("all", "")
        if not full_text:
             raise UserError(_("Could not extract text from the provided file."))
        
        # Heuristic Number Format Detection
        import re
        detected_decimal = False
        detected_thousand = False
        
        # Pattern for 1.234,56 (European)
        if re.search(r'\d{1,3}\.\d{3},\d{2}', full_text):
            detected_decimal = 'comma'
            detected_thousand = 'dot'
        # Pattern for 1,234.56 (US/UK)
        elif re.search(r'\d{1,3},\d{3}\.\d{2}', full_text):
            detected_decimal = 'dot'
            detected_thousand = 'comma'
        # Pattern for 1234,56 (Simple Comma Decimal)
        elif re.search(r'\d{1,3},\d{2}\b', full_text) and not re.search(r'\d{1,3}\.\d{2}\b', full_text):
            detected_decimal = 'comma'
            # Thousand could be dot or space or none, hard to say, but decimal is definitely comma
            if re.search(r'\d\.\d{3}', full_text):
                 detected_thousand = 'dot'
        # Pattern for 1234.56 (Simple Dot Decimal)
        elif re.search(r'\d{1,3}\.\d{2}\b', full_text) and not re.search(r'\d{1,3},\d{2}\b', full_text):
            detected_decimal = 'dot'
            if re.search(r'\d,\d{3}', full_text):
                 detected_thousand = 'comma'

        # 2. Call Ollama
        config = self.env["ir.config_parameter"].sudo()
        endpoint = config.get_param("account_invoice_import_simple_pdf_ocr.ollama_endpoint")
        model = config.get_param("account_invoice_import_simple_pdf_ocr.ollama_model")
        token = config.get_param("account_invoice_import_simple_pdf_ocr.ollama_token")
        
        # Get configurable prompt or fallback to default
        default_prompt = """
        You are a regex expert.
Analyze the following invoice text and extract:
1. Regex pattern for 'Amount Total' (e.g. ^Total\s+([\d,.]+)$)
2. Regex pattern for 'Invoice Date'
3. Regex pattern for 'Invoice Number'
4. Regex pattern for 'Untaxed Amount' (if present)
5. Regex pattern for 'Tax Amount' (if present)
6. Date Format found in text (options: dd-mm-y4, dd-month-y4, month-dd-y4, mm-dd-y4, y4-mm-dd, dd-mm-y2, dd-month-y2, month-dd-y2, mm-dd-y2)
7. Date Separator found in text (options: slash, dash, dot, space)
8. Decimal Separator (options: dot, comma)
9. Thousand Separator (options: none, space, dot, comma, apostrophe)
10. A unique keyword to identify this supplier (e.g. 'Amazon', 'Uber')

Return ONLY a JSON object with keys: 'amount_total', 'date', 'invoice_number', 'amount_untaxed', 'amount_tax', 'date_format', 'date_separator', 'decimal_separator', 'thousand_separator', 'keyword'.
If a field is not found, use null.
The value of each key must be another object with properties: 'value' (the extracted text) and 'regex' (a python regex string to extract it).
The regex should be as specific as possible but robust.
        
        Text:
        {text}
        """
        prompt_template = config.get_param("account_invoice_import_simple_pdf_ocr.ollama_prompt", default_prompt)
        
        # Format the prompt with the extracted text
        # We use simple string replacement or format if fails
        try:
             prompt = prompt_template.format(text=full_text[:4000])
        except Exception:
             # Fallback if user messed up format placeholders
             prompt = prompt_template + "\n\nText:\n" + full_text[:4000]
        
        try:
             headers = {}
             if token:
                 headers["Authorization"] = f"Bearer {token}"
            
             response = requests.post(endpoint, json={
                 "model": model,
                 "prompt": prompt,
                 "stream": False,
                 "format": "json"
             }, headers=headers, timeout=120)
             response.raise_for_status()
             result = response.json()
             response_text = result.get("response", "{}")
             ai_data = json.loads(response_text)
             
             # 3. Apply rules to partner
             # Map Odoo fields to JSON keys
             # The AI response provides a dictionary for each field with 'value' and 'regex'.
             # We need to extract the 'regex' part.
             
             # 3. Apply rules to partner
             
             # Default settings for mandatory fields
             # These match the defaults from res_partner.pdf_simple_generate_default_fields
             default_field_configs = {
                 "amount_total": {"extract_rule": "max", "position": 2},
                 "amount_untaxed": {"extract_rule": "position_end", "position": 3},
                 "invoice_number": {"extract_rule": "first", "position": 2},
                 "date": {"extract_rule": "first", "position": 2},
             }
             
             # Map Odoo fields to JSON keys from AI response
             field_mappings = {
                 "amount_total": "amount_total",
                 "date": "date",
                 "invoice_number": "invoice_number",
                 "amount_untaxed": "amount_untaxed",
                 "amount_tax": "amount_tax",
             }

             # Set of fields we want to ensure exist (mandatory ones)
             mandatory_fields = set(default_field_configs.keys())
             
             # Process mandatory fields + any optional ones found by AI
             fields_to_process = mandatory_fields.union(set(field_mappings.keys()))

             for odoo_field in fields_to_process:
                 ai_key = field_mappings.get(odoo_field)
                 ai_field_data = ai_key and ai_data.get(ai_key)
                 
                 # Determine regex and extract_rule
                 vals = {}
                 
                 # Special Case: For amount_total, User prefers "Highest Value" heuristic
                 # which is more robust than AI regex on small models.
                 # So we intentionally IGNORE AI regex for amount_total and force 'max'
                 if odoo_field == 'amount_total':
                     vals.update(default_field_configs["amount_total"])
                     # Ensure regexp is False so simple_pdf uses default number patterns
                     vals["regexp"] = False 
                     
                 elif ai_field_data and isinstance(ai_field_data, dict) and ai_field_data.get("regex"):
                     # AI found a pattern (for other fields)
                     vals["regexp"] = ai_field_data.get("regex")
                     # If AI found a specific regex, usually 'first' match is what we want
                     vals["extract_rule"] = "first" 
                 elif odoo_field in default_field_configs:
                     # Fallback to default if mandatory and not found by AI
                     vals.update(default_field_configs[odoo_field])
                 else:
                     # Optional field not found by AI, skip
                     continue

                 # Explicitly set date format/separator on the field line for visibility
                 if odoo_field == 'date':
                     d_fmt = ai_data.get("date_format") or "dd-mm-y4"
                     d_sep = map_separator(ai_data.get("date_separator"), 'date') or "slash"
                     vals["date_format"] = d_fmt
                     vals["date_separator"] = d_sep

                 # Check if field exists
                 field_rec = self.partner_id.simple_pdf_field_ids.filtered(lambda f: f.name == odoo_field)
                 if field_rec:
                     field_rec.write(vals)
                 else:
                     vals["name"] = odoo_field
                     vals["partner_id"] = self.partner_id.id
                     self.partner_id.write({
                         "simple_pdf_field_ids": [(0, 0, vals)]
                     })
             
             # Save Partner Config (Global defaults)
             partner_vals = {}
             
             # Default to dd-mm-y4 and slash if AI detection fails, as these are mandatory
             date_fmt = ai_data.get("date_format")
             date_sep = ai_data.get("date_separator")
             
             partner_vals["simple_pdf_date_format"] = date_fmt or "dd-mm-y4"
             partner_vals["simple_pdf_date_separator"] = map_separator(date_sep, 'date') or "slash"
             
             if ai_data.get("decimal_separator"):
                 partner_vals["simple_pdf_decimal_separator"] = map_separator(ai_data.get("decimal_separator"), 'decimal')
             if detected_decimal:
                 # Override with heuristic if available
                 partner_vals["simple_pdf_decimal_separator"] = detected_decimal
                 
             if ai_data.get("thousand_separator"):
                 partner_vals["simple_pdf_thousand_separator"] = map_separator(ai_data.get("thousand_separator"), 'thousand')
             if detected_thousand:
                 # Override with heuristic if available
                 partner_vals["simple_pdf_thousand_separator"] = detected_thousand
                 
             if ai_data.get("keyword"):
                 partner_vals["simple_pdf_keyword"] = ai_data.get("keyword")

             if partner_vals:
                self.partner_id.write(partner_vals)


             
        except Exception as e:
            _logger.error("AI Analysis failed: %s", e)
            raise UserError(_("AI Analysis failed. Check logs for details. Error: %s") % str(e))
            
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Extraction rules detected and applied!"),
                "type": "success",
                "sticky": False,
            }
        }
