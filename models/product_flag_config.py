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

    @api.constrains(
        'ft_advstock_flag_yellow_min',
        'ft_advstock_flag_green_min',
        'ft_advstock_flag_green_max',
        'ft_advstock_flag_yellow_max',
    )
    def _check_flag_ranges(self):
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


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ft_advstock_has_custom_flag = fields.Boolean(
        string='Usar Flags de Rotación Personalizadas',
        compute='_compute_flag_fields',
        inverse='_inverse_flag_fields',
    )
    ft_advstock_flag_yellow_min = fields.Integer(
        string='Amarillo Min (días)',
        compute='_compute_flag_fields',
        inverse='_inverse_flag_fields',
    )
    ft_advstock_flag_green_min = fields.Integer(
        string='Verde Min (días)',
        compute='_compute_flag_fields',
        inverse='_inverse_flag_fields',
    )
    ft_advstock_flag_green_max = fields.Integer(
        string='Verde Max (días)',
        compute='_compute_flag_fields',
        inverse='_inverse_flag_fields',
    )
    ft_advstock_flag_yellow_max = fields.Integer(
        string='Amarillo Max (días)',
        compute='_compute_flag_fields',
        inverse='_inverse_flag_fields',
    )

    def _get_flag_config(self):
        """Return the flag config record for this product and current company, or False."""
        self.ensure_one()
        return self.env['ft.advstock.product.flag'].search([
            ('product_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    @api.depends_context('company')
    def _compute_flag_fields(self):
        company = self.env.company
        FlagConfig = self.env['ft.advstock.product.flag']
        # Batch fetch all configs for these products in current company
        configs = FlagConfig.search([
            ('product_id', 'in', self.ids),
            ('company_id', '=', company.id),
        ])
        config_map = {c.product_id.id: c for c in configs}

        for product in self:
            config = config_map.get(product.id)
            if config:
                product.ft_advstock_has_custom_flag = True
                product.ft_advstock_flag_yellow_min = config.ft_advstock_flag_yellow_min
                product.ft_advstock_flag_green_min = config.ft_advstock_flag_green_min
                product.ft_advstock_flag_green_max = config.ft_advstock_flag_green_max
                product.ft_advstock_flag_yellow_max = config.ft_advstock_flag_yellow_max
            else:
                product.ft_advstock_has_custom_flag = False
                product.ft_advstock_flag_yellow_min = company.ft_advstock_flag_yellow_min
                product.ft_advstock_flag_green_min = company.ft_advstock_flag_green_min
                product.ft_advstock_flag_green_max = company.ft_advstock_flag_green_max
                product.ft_advstock_flag_yellow_max = company.ft_advstock_flag_yellow_max

    def _inverse_flag_fields(self):
        FlagConfig = self.env['ft.advstock.product.flag']
        company = self.env.company
        for product in self:
            config = FlagConfig.search([
                ('product_id', '=', product.id),
                ('company_id', '=', company.id),
            ], limit=1)

            if product.ft_advstock_has_custom_flag:
                vals = {
                    'ft_advstock_flag_yellow_min': product.ft_advstock_flag_yellow_min,
                    'ft_advstock_flag_green_min': product.ft_advstock_flag_green_min,
                    'ft_advstock_flag_green_max': product.ft_advstock_flag_green_max,
                    'ft_advstock_flag_yellow_max': product.ft_advstock_flag_yellow_max,
                }
                if config:
                    config.write(vals)
                else:
                    FlagConfig.create({
                        'product_id': product.id,
                        'company_id': company.id,
                        **vals,
                    })
            else:
                if config:
                    config.unlink()
