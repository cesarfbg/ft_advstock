from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    ft_advstock_license_token = fields.Char(
        string='Token de Licencia (Inventario Avanzado)',
        help='Token proporcionado por Feral Tech para la validación de licencia de Inventario Avanzado.',
    )
    ft_advstock_use_decimals = fields.Boolean(
        string='Mostrar Decimales',
        default=False,
        help='Mostrar valores numéricos con 2 decimales en los reportes. '
             'Si está desactivado, los números se redondean a enteros.',
    )
    ft_advstock_flag_yellow_min = fields.Integer(
        string='Límite Inferior Amarillo (días)',
        default=25,
        help='Por debajo de este valor la rotación se marca en rojo (déficit).',
    )
    ft_advstock_flag_green_min = fields.Integer(
        string='Límite Inferior Verde (días)',
        default=30,
        help='Inicio del rango de rotación saludable.',
    )
    ft_advstock_flag_green_max = fields.Integer(
        string='Límite Superior Verde (días)',
        default=60,
        help='Fin del rango de rotación saludable.',
    )
    ft_advstock_flag_yellow_max = fields.Integer(
        string='Límite Superior Amarillo (días)',
        default=65,
        help='Por encima de este valor la rotación se marca en rojo (exceso).',
    )
    ft_advstock_excluded_location_ids = fields.Many2many(
        'stock.location',
        'ft_advstock_excluded_location_rel',
        'company_id',
        'location_id',
        string='Ubicaciones Excluidas (Planeación)',
        help='Ubicaciones de inventario que se excluyen del cálculo de inventario inicial en la planeación.',
    )
    ft_advstock_planning_picking_type_ids = fields.Many2many(
        'stock.picking.type',
        'ft_advstock_planning_picking_type_rel',
        'company_id',
        'picking_type_id',
        string='Tipos de Operación (Ventas Reales)',
        help='Tipos de operación que se consideran como "salidas" para el cálculo de ventas reales.',
    )

    _FLAG_FIELDS = {
        'ft_advstock_flag_yellow_min',
        'ft_advstock_flag_green_min',
        'ft_advstock_flag_green_max',
        'ft_advstock_flag_yellow_max',
    }

    def write(self, vals):
        res = super().write(vals)
        if self._FLAG_FIELDS & set(vals.keys()):
            self._validate_flag_ranges()
        return res

    def _validate_flag_ranges(self):
        for company in self:
            y_min = company.ft_advstock_flag_yellow_min
            g_min = company.ft_advstock_flag_green_min
            g_max = company.ft_advstock_flag_green_max
            y_max = company.ft_advstock_flag_yellow_max
            if y_min >= g_min:
                raise ValidationError(
                    _('El límite inferior amarillo (%s) debe ser menor que el límite inferior verde (%s).')
                    % (y_min, g_min)
                )
            if g_max <= g_min:
                raise ValidationError(
                    _('El límite superior verde (%s) debe ser mayor que el límite inferior verde (%s).')
                    % (g_max, g_min)
                )
            if y_max <= g_max:
                raise ValidationError(
                    _('El límite superior amarillo (%s) debe ser mayor que el límite superior verde (%s).')
                    % (y_max, g_max)
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
    ft_advstock_use_decimals = fields.Boolean(
        related='company_id.ft_advstock_use_decimals',
        readonly=False,
    )
    ft_advstock_flag_yellow_min = fields.Integer(
        related='company_id.ft_advstock_flag_yellow_min',
        readonly=False,
    )
    ft_advstock_flag_green_min = fields.Integer(
        related='company_id.ft_advstock_flag_green_min',
        readonly=False,
    )
    ft_advstock_flag_green_max = fields.Integer(
        related='company_id.ft_advstock_flag_green_max',
        readonly=False,
    )
    ft_advstock_flag_yellow_max = fields.Integer(
        related='company_id.ft_advstock_flag_yellow_max',
        readonly=False,
    )
    ft_advstock_excluded_location_ids = fields.Many2many(
        related='company_id.ft_advstock_excluded_location_ids',
        readonly=False,
    )
    ft_advstock_planning_picking_type_ids = fields.Many2many(
        related='company_id.ft_advstock_planning_picking_type_ids',
        readonly=False,
    )
