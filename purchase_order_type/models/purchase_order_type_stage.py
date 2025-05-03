from odoo import models, fields

class PurchaseOrderTypeStage(models.Model):
    _name = 'purchase.order.type.stage'
    _description = 'Purchase Order Type Stage'

    name = fields.Char(string='نام وضعیت', required=True)
    sequence = fields.Integer(string='ترتیب', default=10)
    order_type_id = fields.Many2one('purchase.order.type', string='Order Type', required=True, ondelete='cascade')
    group_id = fields.Many2one('res.groups', string='دسترسی به گروه', required=True)