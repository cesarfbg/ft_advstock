from odoo import models


class AdvancedStockReportsLicense(models.AbstractModel):
    _name = 'advanced.stock.reports.license'
    _inherit = 'feral.tech.license.mixin'
    _description = 'Inventario Avanzado - License Manager'

    _app_code = 'ft_advstock'
    _app_version = '16.0'
    _token_field = 'ft_advstock_license_token'
    _log_prefix = '[LIC]'
    _module_label = 'Inventario Avanzado'
