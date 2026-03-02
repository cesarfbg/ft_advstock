from odoo import api, fields, models


def _normalize_to_first(date):
    """Force any date to the 1st day of its month."""
    return date.replace(day=1) if date else date


class LogisticsForecast(models.Model):
    _name = 'ft.advstock.logistics.forecast'
    _description = 'Presupuesto Logístico por Producto/Mes'
    _order = 'product_id, month_date'
    _rec_name = 'product_id'
    _sql_constraints = [
        ('product_month_company_uniq',
         'unique(product_id, month_date, company_id)',
         'Ya existe un presupuesto para este producto en este mes y compañía.'),
    ]

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_categ_id = fields.Many2one(
        related='product_id.categ_id',
        string='Categoría',
        store=True,
    )
    month_date = fields.Date(
        string='Mes',
        required=True,
        help='Primer día del mes al que corresponde el presupuesto.',
    )
    quantity = fields.Float(
        string='Cantidad Presupuestada',
        default=0.0,
        help='Cantidad estimada de venta/salida para este producto en este mes.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @api.onchange('month_date')
    def _onchange_month_date(self):
        if self.month_date:
            self.month_date = _normalize_to_first(self.month_date)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('month_date'):
                vals['month_date'] = _normalize_to_first(
                    fields.Date.to_date(vals['month_date'])
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('month_date'):
            vals['month_date'] = _normalize_to_first(
                fields.Date.to_date(vals['month_date'])
            )
        return super().write(vals)
