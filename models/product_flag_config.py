from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductFlagConfig(models.Model):
    _name = 'ft.advstock.product.flag'
    _description = 'Configuración de Flags de Rotación por Producto'
    _order = 'product_id'
    _rec_name = 'product_id'
    _sql_constraints = [
        ('product_company_uniq', 'unique(product_id, company_id)',
         'Ya existe una configuración de flags para este producto en esta compañía.'),
    ]

    _FLAG_FIELDS = {
        'ft_advstock_flag_yellow_min',
        'ft_advstock_flag_green_min',
        'ft_advstock_flag_green_max',
        'ft_advstock_flag_yellow_max',
    }

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='cascade',
    )
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='Plantilla',
        store=True,
    )
    categ_id = fields.Many2one(
        related='product_id.categ_id',
        string='Categoría',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    ft_advstock_flag_yellow_min = fields.Integer(
        string='Límite Inferior Amarillo (días)',
        required=True,
        default=25,
    )
    ft_advstock_flag_green_min = fields.Integer(
        string='Límite Inferior Verde (días)',
        required=True,
        default=30,
    )
    ft_advstock_flag_green_max = fields.Integer(
        string='Límite Superior Verde (días)',
        required=True,
        default=60,
    )
    ft_advstock_flag_yellow_max = fields.Integer(
        string='Límite Superior Amarillo (días)',
        required=True,
        default=65,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._validate_flag_ranges()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self._FLAG_FIELDS & set(vals.keys()):
            self._validate_flag_ranges()
        return res

    def _validate_flag_ranges(self):
        for rec in self:
            y_min = rec.ft_advstock_flag_yellow_min
            g_min = rec.ft_advstock_flag_green_min
            g_max = rec.ft_advstock_flag_green_max
            y_max = rec.ft_advstock_flag_yellow_max
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
