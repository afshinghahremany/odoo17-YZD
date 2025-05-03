from odoo import models, fields

class PurchaseOrderStageLog(models.Model):
    _name = 'purchase.order.stage.log'
    _description = 'Purchase Order Stage Log'
    _order = 'date desc'

    order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True, ondelete='cascade')
    stage_id = fields.Many2one('purchase.order.type.stage', string='Stage', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)