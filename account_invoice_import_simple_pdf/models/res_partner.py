# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_amount, format_date, format_datetime

logger = logging.getLogger(__name__)
ERROR_STYLE = ' style="color:red;"'
SEPARATOR_INVERT_MAP = {
    "comma": "dot",
    "dot": "comma",
}

try:
    import regex
except ImportError:
    logger.debug("Cannot import regex")


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _simple_pdf_date_format_sel(self):
        return [
            ("dd-mm-y4", _("DD MM AAAA")),
            ("dd-month-y4", _("DD Mes AAAA")),
            ("month-dd-y4", _("Mes DD AAAA")),
            ("mm-dd-y4", _("MM DD AAAA")),
            ("y4-mm-dd", _("AAAA MM DD")),
            ("dd-mm-y2", _("DD MM AA")),
            ("dd-month-y2", _("DD Mes AA")),
            ("month-dd-y2", _("Mes DD AA")),
            ("mm-dd-y2", _("MM DD AA")),
        ]

    @api.model
    def _simple_pdf_date_separator_sel(self):
        return [
            ("slash", "/"),
            ("dash", _("guión")),
            ("dot", _("punto")),
            ("space", _("espacio")),
        ]

    simple_pdf_keyword = fields.Char(
        string="Palabra Clave PDF Simple",
        help="Si está vacío, Odoo usará el número de IVA para identificar al proveedor. "
        "Para coincidir con varias palabras clave, sepárelas con '|' (pipe)."
    )
    # Temporary hack: I disable the default values for the fields
    # simple_pdf_date_format and simple_pdf_date_separator
    # to avoid the following bug:
    # https://github.com/odoo/odoo/issues/75492
    simple_pdf_date_format = fields.Selection(
        "_simple_pdf_date_format_sel",
        string="Formato de Fecha",
        # default="dd-mm-y4",
        help="Si el formato de fecha usa 'Mes', verifica que el idioma esté "
        "configurado correctamente en el proveedor. 'Mes' funciona tanto en versión completa como "
        "corta ('Enero' y 'Ene.').",
    )
    simple_pdf_date_separator = fields.Selection(
        "_simple_pdf_date_separator_sel",
        # default="slash",
        string="Separador de Fecha",
        compute="_compute_simple_pdf_date_separator",
        readonly=False,
        precompute=True,
        store=True,
        help="Si la fecha se ve como 'Sep. 4, 2021', usa 'espacio' como separador "
        "de fecha (Odoo ignorará el punto y la coma).",
    )
    simple_pdf_decimal_separator = fields.Selection(
        [
            ("dot", "punto"),
            ("comma", "coma"),
        ],
        string="Separador Decimal",
        compute="_compute_simple_pdf_decimal_separator",
        readonly=False,
        precompute=True,
        store=True,
        help="Si está vacío, Odoo usará el separador decimal configurado en "
        "el idioma del proveedor.",
    )
    simple_pdf_thousand_separator = fields.Selection(
        [
            ("none", "ninguno"),
            ("space", "espacio"),
            ("dot", "punto"),
            ("comma", "coma"),
            ("apostrophe", "apóstrofe"),
        ],
        string="Separador de Miles",
        compute="_compute_simple_pdf_thousand_separator",
        readonly=False,
        precompute=True,
        store=True,
        help="Si está vacío, Odoo usará el separador de miles configurado en "
        "el idioma del proveedor.",
    )
    simple_pdf_pages = fields.Selection(
        [
            ("first", "Solo Primera Página"),
            ("all", "Todas las Páginas"),
        ],
        default="all",
        string="Análisis de Página",
    )
    simple_pdf_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de Importación de Factura",
        ondelete="restrict",
        help="Si está vacío, Odoo usará la moneda de la compañía.",
    )
    simple_pdf_field_ids = fields.One2many(
        "account.invoice.import.simple.pdf.fields",
        "partner_id",
        string="Campos para Importación de Factura PDF",
    )
    simple_pdf_invoice_number_ids = fields.One2many(
        "account.invoice.import.simple.pdf.invoice.number",
        "partner_id",
        string="Formato de Número de Importación de Factura",
    )
    simple_pdf_test_file = fields.Binary(
        string="Archivo PDF de Factura de Prueba", attachment=True
    )
    simple_pdf_test_filename = fields.Char(string="Nombre de Archivo PDF de Prueba")
    simple_pdf_test_raw_text = fields.Text(string="Extracción de Texto de Prueba", readonly=True)
    simple_pdf_test_results = fields.Html(string="Resultados de la Prueba", readonly=True)

    @api.constrains("simple_pdf_decimal_separator", "simple_pdf_thousand_separator")
    def _check_simple_pdf_separator(self):
        for partner in self:
            if (
                partner.simple_pdf_decimal_separator
                and partner.simple_pdf_decimal_separator
                == partner.simple_pdf_thousand_separator
            ):
                raise ValidationError(
                    _(
                        "Para el proveedor '%s', el separador decimal no puede ser "
                        "el mismo que el separador de miles."
                    )
                    % partner.display_name
                )

    @api.depends("simple_pdf_decimal_separator")
    def _compute_simple_pdf_thousand_separator(self):
        for partner in self:
            if (
                partner.simple_pdf_decimal_separator
                and partner.simple_pdf_decimal_separator
                == partner.simple_pdf_thousand_separator
            ):
                partner.simple_pdf_thousand_separator = SEPARATOR_INVERT_MAP.get(
                    partner.simple_pdf_decimal_separator
                )

    @api.depends("simple_pdf_thousand_separator")
    def _compute_simple_pdf_decimal_separator(self):
        for partner in self:
            if (
                partner.simple_pdf_thousand_separator
                and partner.simple_pdf_thousand_separator
                == partner.simple_pdf_decimal_separator
            ):
                partner.simple_pdf_decimal_separator = SEPARATOR_INVERT_MAP.get(
                    partner.simple_pdf_thousand_separator
                )

    @api.depends("simple_pdf_date_format")
    def _compute_simple_pdf_date_separator(self):
        for partner in self:
            if (
                partner.simple_pdf_date_format
                and "month" in partner.simple_pdf_date_format
            ):
                partner.simple_pdf_date_separator = "space"

    def _prepare_simple_pdf_invoice_number_regex(self):
        self.ensure_one()
        if not self.simple_pdf_invoice_number_ids:
            raise UserError(
                _("Falta la configuración del formato del número de factura en el proveedor '%s'.")
                % self.display_name
            )
        regex = []
        for entry in self.simple_pdf_invoice_number_ids:
            entry._prepare_invoice_number_regex(regex)
        regex_string = "".join(regex)
        return regex_string

    def pdf_simple_generate_default_fields(self):
        self.ensure_one()
        assert not self.parent_id
        assert self.is_company
        assert not self.simple_pdf_field_ids
        def_fields = [
            {"name": "amount_total", "extract_rule": "max"},
            {"name": "amount_untaxed", "extract_rule": "position_end", "position": 3},
            {"name": "invoice_number", "extract_rule": "first"},
            {"name": "date", "extract_rule": "first"},
        ]
        self.write(
            {
                "simple_pdf_field_ids": [(0, 0, field_val) for field_val in def_fields],
            }
        )

    def pdf_simple_test_cleanup(self):
        self.ensure_one()
        self.write(
            {
                "simple_pdf_test_raw_text": False,
                "simple_pdf_test_results": False,
                "simple_pdf_test_filename": False,
                "simple_pdf_test_file": False,
            }
        )

    def pdf_simple_test_run(self):
        self.ensure_one()
        aiio = self.env["account.invoice.import"]
        rpo = self.env["res.partner"]
        vals = {}
        test_results = []
        test_results.append("<small>%s</small><br/>" % _("Los errores están en rojo."))
        test_results.append(
            "<small>%s %s</small><br/>"
            % (_("Fecha de Prueba:"), format_datetime(self.env, fields.Datetime.now()))
        )
        if not self.simple_pdf_test_file:
            raise UserError(_("Debes subir una factura PDF de prueba."))
        test_info = {"test_mode": True}
        aiio._simple_pdf_update_test_info(test_info)
        file_data = base64.b64decode(self.simple_pdf_test_file)
        raw_text_dict = aiio.simple_pdf_text_extraction(file_data, test_info)
        test_results.append(
            "<small>%s %s</small><br/>"
            % (
                _("Parámetro del sistema de extracción de texto:"),
                test_info.get("text_extraction_config") or _("ninguno"),
            )
        )
        test_results.append(
            "<small>%s %s</small><br/>"
            % (_("Herramienta de extracción de texto utilizada:"), test_info.get("text_extraction"))
        )
        if self.simple_pdf_pages == "first":
            vals["simple_pdf_test_raw_text"] = raw_text_dict["first"]
        else:
            vals["simple_pdf_test_raw_text"] = raw_text_dict["all"]
        test_results.append("<h3>%s</h3><ul>" % _("Buscando Proveedor"))
        partner_id = aiio.simple_pdf_match_partner(
            raw_text_dict["all_no_space"], test_results
        )
        partner_ok = False
        if partner_id:
            partner = rpo.browse(partner_id)
            if partner_id == self.id:
                partner_ok = True
                partner_result = _("Proveedor actual encontrado")
            else:
                partner_result = "%s %s" % (
                    _("Se encontró otro proveedor:"),
                    partner.display_name,
                )
        else:
            partner_result = _("No se encontró ningún proveedor.")
        test_results.append(
            "<li><b>%s</b> <b%s>%s</b></li></ul>"
            % (_("Resultado:"), not partner_ok and ERROR_STYLE or "", partner_result)
        )
        if partner_ok:
            partner_config = self._simple_pdf_partner_config()
            test_results.append("<h3>%s</h3><ul>" % _("Configuración de Importe"))
            test_results.append(
                """<li>%s "%s" (%s)</li>"""
                % (
                    _("Separador Decimal:"),
                    partner_config["decimal_sep"],
                    partner_config["char2separator"].get(
                        partner_config["decimal_sep"], _("desconocido")
                    ),
                )
            )
            test_results.append(
                """<li>%s "%s" (%s)</li></ul>"""
                % (
                    _("Separador de Miles:"),
                    partner_config["thousand_sep"],
                    partner_config["char2separator"].get(
                        partner_config["thousand_sep"], _("desconocido")
                    ),
                )
            )
            parsed_inv = aiio.simple_pdf_parse_invoice(file_data, test_info)
            key2label = {
                "pattern": _("Expresión Regular"),
                "date_format": _("Formato de Fecha"),
                "res_regex": _("Lista Bruta"),
                "valid_list": _("Lista Filtrada de Datos Válidos"),
                "sorted_list": _("Lista Ordenada"),
                "error_msg": _("Mensaje de error"),
                "start": _("Cadena de Inicio"),
                "end": _("Cadena de Fin"),
            }
            for field in self.simple_pdf_field_ids:
                test_results.append(
                    "<h3>%s</h3><ul>" % test_info["field_name_sel"][field.name]
                )
                extract_method = test_info["extract_rule_sel"][field.extract_rule]
                if field.extract_rule.startswith("position_"):
                    extract_method += _(", Posición: %d") % field.position
                test_results.append(
                    "<li>%s %s</li>" % (_("Regla de Extracción:"), extract_method)
                )
                for key, value in test_info[field.name].items():
                    if key != "pattern" or self.env.user.has_group("base.group_system"):
                        test_results.append("<li>%s: %s</li>" % (key2label[key], value))

                result = parsed_inv.get(field.name)
                if "date" in field.name and result:
                    result = format_date(self.env, result)
                if "amount" in field.name and result:
                    result = format_amount(
                        self.env, result, parsed_inv["currency"]["recordset"]
                    )
                test_results.append(
                    "<li><b>%s</b> <b%s>%s</b></li></ul>"
                    % (
                        _("Resultado:"),
                        not result and ERROR_STYLE or "",
                        result or _("Ninguno"),
                    )
                )
        vals["simple_pdf_test_results"] = "\n".join(test_results)
        self.write(vals)

    def _simple_pdf_partner_config(self):
        self.ensure_one()
        separator2char = {
            "slash": "/",
            "dash": "-",
            "dot": ".",
            "comma": ",",
            "space": chr(32),  # regular space
            "apostrophe": "'",
            "none": "",
        }
        char2separator = {val: key for key, val in separator2char.items()}
        date_format2regex = {
            "dd": r"\d{1,2}",  # We have to match on July 4, 2021
            "mm": r"\d{1,2}",
            "y4": r"\d{4}",
            "y2": r"\d{2}",
            "month": r"[\p{L}\p{Mn}]{3,15}\.?",
            # \p{L} : any unicode letter (but not digit)
            # \p{Mn} : non spacing mark, for example \u0301 combining acute accent
            # option dot for short month (e.g. 'feb.')
        }
        date_format2dt = {
            "dd": "%d",
            "mm": "%m",
            "month": "%B",
            "y4": "%Y",
            "y2": "%y",
        }
        lang = False
        if self.lang:
            lang = self.env["res.lang"].search([("code", "=", self.lang)], limit=1)
        if self.simple_pdf_decimal_separator:
            decimal_sep = separator2char[self.simple_pdf_decimal_separator]
        elif lang:
            decimal_sep = lang.decimal_point
        else:
            raise UserError(
                _(
                    "No se pudo obtener el separador decimal para el proveedor '%s': "
                    "los campos 'Idioma' y 'Separador Decimal' están "
                    "ambos vacíos para este proveedor."
                )
                % self.display_name
            )
        if self.simple_pdf_thousand_separator:
            thousand_sep = separator2char[self.simple_pdf_thousand_separator]
        elif lang:
            thousand_sep = lang.thousands_sep
            # Remplace all white space characters (no-break-space, narrow no-break-space)
            # by regular space
            if regex.match(r"^\s$", thousand_sep):
                thousand_sep = chr(32)  # regular space
        else:
            thousand_sep = ""
        if thousand_sep == decimal_sep:
            raise UserError(
                _(
                    "Para el proveedor '%(partner_name)s', el separador decimal "
                    "(%(decimal_sep)s) es el mismo que "
                    "el separador de miles (%(thousand_sep)s). Ten en cuenta que, "
                    "si no se establece explícitamente, el separador decimal y de miles se leen "
                    "del idioma del proveedor.",
                    partner_name=self.display_name,
                    decimal_sep=char2separator.get(decimal_sep),
                    thousand_sep=char2separator.get(thousand_sep),
                )
            )
        logger.debug("decimal_sep=|%s| thousand_sep=|%s|", decimal_sep, thousand_sep)
        partner_config = {
            "recordset": self,
            "display_name": self.display_name,
            "date_format": self.simple_pdf_date_format,
            "date_separator": self.simple_pdf_date_separator,
            "currency": self.simple_pdf_currency_id or self.env.company.currency_id,
            "decimal_sep": decimal_sep,
            "thousand_sep": thousand_sep,
            "separator2char": separator2char,
            "char2separator": char2separator,
            "date_format2regex": date_format2regex,
            "date_format2dt": date_format2dt,
            "lang_short": self.lang and self.lang[:2] or None,
        }
        # Check field list
        field_list = [field.name for field in self.simple_pdf_field_ids]
        amount_total_count = field_list.count("amount_total")
        amount_untaxed_count = field_list.count("amount_untaxed")
        amount_tax = field_list.count("amount_tax")
        amount_fields_count = amount_total_count + amount_untaxed_count + amount_tax
        if "date" not in field_list:
            raise UserError(
                _(
                    "Debes configurar una regla de extracción de campo para "
                    "el campo 'Fecha' para el proveedor '%s'."
                )
                % self.display_name
            )
        if amount_fields_count == 0:
            raise UserError(
                _("No hay ningún campo de importe configurado para el proveedor '%s'.")
                % self.display_name
            )
        if amount_fields_count == 1 and amount_total_count == 0:
            raise UserError(
                _(
                    "Para el proveedor '%s', solo se ha configurado un campo de importe "
                    "pero no es 'Importe Total'."
                )
                % self.display_name
            )
        return partner_config
