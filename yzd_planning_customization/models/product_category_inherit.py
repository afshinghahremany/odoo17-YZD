from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    is_raw_material = fields.Boolean(
        string='مواد اولیه',
        help='این دسته‌بندی برای مواد اولیه است'
    )
