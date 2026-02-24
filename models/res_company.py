from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    ft_advstock_license_token = fields.Char(
        string='Token de Licencia (Inventario Avanzado)',
        help='Token proporcionado por Feral Tech para la validación de licencia de Inventario Avanzado.',
    )

    @api.model
    def _cron_validate_license(self):
        """Called by ir.cron to validate Inventario Avanzado licenses for all companies."""
        self.env['advanced.stock.reports.license'].validate_all_companies()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ft_advstock_license_token = fields.Char(
        related='company_id.ft_advstock_license_token',
        readonly=False,
    )
