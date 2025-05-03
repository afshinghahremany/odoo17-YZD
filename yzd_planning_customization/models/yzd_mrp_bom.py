from odoo import models, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    yzd_resource_id = fields.Many2one(
        'resource.resource',
        string='منبع مرتبط',
        required=True,
        domain=[('resource_type', '=', 'material')],
        help='فقط منابع از نوع متریال قابل انتخاب هستند',
        tracking=True  # اضافه کردن قابلیت tracking
    )