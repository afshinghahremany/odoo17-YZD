from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    stock_others_trust_account_id = fields.Many2one(
        'account.account',
        string='Inventory from Others (Consignment)',
        domain="[('deprecated', '=', False)]",
        help="Account used when receiving consigned stock from partners."
    )
