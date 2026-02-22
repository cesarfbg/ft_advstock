from odoo import fields, models


class ReorderPlanningWizard(models.TransientModel):
    _name = 'reorder.planning.wizard'
    _description = 'Planeación de Reorden'

    name = fields.Char(
        string='Nombre',
        default='Planeación de Reorden',
        readonly=True,
    )
