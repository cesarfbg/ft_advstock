from odoo import fields, models


class PlanningProductWizard(models.TransientModel):
    _name = 'ft.advstock.planning.product.wizard'
    _description = 'Selector de Producto para Planeación'

    product_id = fields.Many2one(
        'product.product', string='Producto', required=True,
    )

    def action_go(self):
        """Find or create the planning for the selected product, then open it."""
        Planning = self.env['ft.advstock.purchase.planning']
        company = self.env.company
        today_first = fields.Date.today().replace(day=1)
        existing = Planning.search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', company.id),
        ], limit=1)
        if not existing:
            existing = Planning.create({
                'product_id': self.product_id.id,
                'company_id': company.id,
                'center_date': today_first,
            })
        else:
            existing.center_date = today_first
            existing._do_refresh(reset_projections=True)
        return existing._reload_form()
