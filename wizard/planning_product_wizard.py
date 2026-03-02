from odoo import fields, models


class PlanningProductWizard(models.TransientModel):
    _name = 'ft.advstock.planning.product.wizard'
    _description = 'Selector de Producto para Planeación'

    product_id = fields.Many2one(
        'product.product', string='Producto', required=True,
    )

    def action_go(self):
        """Create a fresh transient planning and open it."""
        planning = self.env['ft.advstock.purchase.planning'].create({
            'product_id': self.product_id.id,
            'company_id': self.env.company.id,
            'center_date': fields.Date.today().replace(day=1),
        })
        return planning._reload_form()
