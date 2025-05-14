from odoo import models, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    operation_id = fields.Many2one(
        'resource.resource',
        string='Operation',
        required=False,  # اختیاری
        domain=[('resource_type', '=', 'material')],
        tracking=True
    )
