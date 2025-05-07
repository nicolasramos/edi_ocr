# Copyright 2015-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountInvoiceImportConfig(models.Model):
    _name = "account.invoice.import.config"
    _description = "Configuración para la importación de Facturas de Proveedor"
    _order = "sequence"
    _check_company_auto = True

    name = fields.Char(required=True, string="Nombre")
    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        ondelete="cascade",
        domain=[("parent_id", "=", False)],
    )
    active = fields.Boolean(default=True, string="Activo")
    sequence = fields.Integer(string="Secuencia")
    invoice_line_method = fields.Selection(
        [
            ("1line_no_product", "Línea única, Sin Producto"),
            ("1line_static_product", "Línea única, Producto Estático"),
            ("nline_no_product", "Múltiples Líneas, Sin Producto"),
            ("nline_static_product", "Múltiples Líneas, Producto Estático"),
            ("nline_auto_product", "Múltiples Líneas, Producto Auto-seleccionado"),
        ],
        string="Método para Línea de Factura",
        required=True,
        default="1line_no_product",
        help="Los métodos de múltiples líneas no funcionarán para facturas PDF "
        "que no tengan un archivo XML incrustado con información estructurada "
        "en cada línea.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        ondelete="cascade",
        required=True,
        default=lambda self: self.env.company,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Cuenta de Gasto",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    account_analytic_id = fields.Many2one(
        "account.analytic.account", string="Cuenta Analítica", check_company=True
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Forzar Diario de Compra",
        check_company=True,
        domain="[('company_id', '=', company_id), ('type', '=', 'purchase')]",
        help="Si está vacío, Odoo usará el primer diario de compra.",
    )
    label = fields.Char(
        string="Forzar Descripción",
        help="Forzar descripción de la línea de factura de proveedor",
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Impuestos",
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        check_company=True,
    )
    static_product_id = fields.Many2one(
        "product.product",
        string="Producto Estático",
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    @api.constrains("invoice_line_method", "account_id", "static_product_id")
    def _check_import_config(self):
        for config in self:
            if (
                "static_product" in config.invoice_line_method
                and not config.static_product_id
            ):
                raise ValidationError(
                    _(
                        "Se debe establecer el Producto Estático en la configuración "
                        "de importación de facturas del proveedor '%s' que tiene un "
                        "Método para Línea de Factura establecido en 'Línea única, "
                        "Producto Estático' o 'Múltiples Líneas, Producto Estático'."
                    )
                    % config.partner_id.name
                )
            if "no_product" in config.invoice_line_method and not config.account_id:
                raise ValidationError(
                    _(
                        "Se debe establecer la Cuenta de Gasto en la configuración "
                        "de importación de facturas del proveedor '%s' que tiene un "
                        "Método para Línea de Factura establecido en 'Línea única, "
                        "Sin Producto' o 'Múltiples Líneas, Sin Producto'."
                    )
                    % config.partner_id.name
                )

    @api.onchange("invoice_line_method", "account_id")
    def invoice_line_method_change(self):
        if self.invoice_line_method == "1line_no_product" and self.account_id:
            self.tax_ids = [(6, 0, self.account_id.tax_ids.ids)]
        elif self.invoice_line_method != "1line_no_product":
            self.tax_ids = [(6, 0, [])]

    def convert_to_import_config(self):
        self.ensure_one()
        vals = {
            "invoice_line_method": self.invoice_line_method,
            "account_analytic": self.account_analytic_id or False,
            "journal": self.journal_id or False,
        }
        if self.invoice_line_method == "1line_no_product":
            vals["account"] = self.account_id
            vals["taxes"] = self.tax_ids
            vals["label"] = self.label or False
        elif self.invoice_line_method == "1line_static_product":
            vals["product"] = self.static_product_id
            vals["label"] = self.label or False
        elif self.invoice_line_method == "nline_no_product":
            vals["account"] = self.account_id
        elif self.invoice_line_method == "nline_static_product":
            vals["product"] = self.static_product_id
        return vals
