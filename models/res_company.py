from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    license_token = fields.Char(
        string='Token de Licencia',
        help='Token proporcionado por Feral Tech para la validación de licencia de Inventario Avanzado.',
    )

    @api.model
    def _cron_validate_license(self):
        """Called by ir.cron to validate the license daily."""
        self.env['advanced.stock.reports.license'].validate_license()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    license_token = fields.Char(
        related='company_id.license_token',
        readonly=False,
    )
