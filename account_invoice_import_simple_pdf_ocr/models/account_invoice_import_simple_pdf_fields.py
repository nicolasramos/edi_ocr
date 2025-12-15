# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>
import logging
from odoo import _, fields, models
import regex

logger = logging.getLogger(__name__)

class AccountInvoiceImportSimplePdfFields(models.Model):
    _inherit = "account.invoice.import.simple.pdf.fields"

    def _selection_name(self):
        selection = super()._selection_name() if hasattr(super(), '_selection_name') else []
        # Fallback if the method doesn't exist (e.g. if it was defined as a list in the parent)
        # But wait, looking at the parent code, 'name' is a Selection field with a list, no dynamic method initially.
        # So in Odoo 17, extending a selection is done via selection_add.
        return selection

    # We use selection_add to extend the field
    name = fields.Selection(
        selection_add=[("analytic_distribution", "Analytic Account")],
        ondelete={"analytic_distribution": "cascade"},
    )

    def _get_analytic_distribution(self, parsed_inv, raw_text, partner_config, test_info):
        self.ensure_one()
        pattern = self.regexp
        test_info[self.name] = {"pattern": pattern}
        restrict_text = self.restrict_text(raw_text, test_info)
        res_regex = regex.findall(pattern, restrict_text)
        test_info[self.name]["res_regex"] = res_regex
        
        # Get the extracted value (e.g., Code or Name of the analytic account)
        extracted_value = self.get_value_from_list(
            res_regex, test_info, raise_if_none=False
        )
        
        if extracted_value:
            extracted_value = extracted_value.strip()
            # Search for the analytic account
            # We search by code or name (case insensitive)
            domain = ['|', ('code', '=ilike', extracted_value), ('name', '=ilike', extracted_value)]
            # It's safer to limit to the current company if possible, but analytic accounts can be shared or restricted differently.
            # Usually, they are company dependent or check_company=True. 
            # Let's rely on standard search which handles record rules.
            
            analytic_account = self.env['account.analytic.account'].search(domain, limit=1)
            
            if analytic_account:
                # Format for analytic_distribution is {str(account_id): percentage}
                # We assume 100% distribution
                parsed_inv[self.name] = {str(analytic_account.id): 100}
                logger.debug(f"Found analytic account: {analytic_account.name} ({analytic_account.code}) for value '{extracted_value}'")
            else:
                logger.warning(f"Analytic Account not found for extracted value: '{extracted_value}'")
                parsed_inv["failed_fields"].append(self.name)
        else:
            parsed_inv["failed_fields"].append(self.name)
