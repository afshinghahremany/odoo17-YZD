from odoo import models, fields, api, _

class PurchaseRequestType(models.Model):
    _name = 'purchase.request.type'
    _description = 'Purchase Request Type'

    name = fields.Char(string='عنوان', required=True)
    approver_id = fields.Many2one('res.users', string='تایید کننده', required=True)
    manual_creation = fields.Boolean(string='امکان ثبت دستی', default=True,
                                   help='اگر این گزینه فعال باشد، کاربران می‌توانند این نوع درخواست را به صورت دستی ثبت کنند')
    qty_readonly = fields.Boolean(string='مقدار فقط خواندنی', default=False,
                                help='اگر این گزینه فعال باشد، فیلد مقدار در لاین‌های درخواست فقط خواندنی خواهد بود')
    date_required_readonly = fields.Boolean(string='تاریخ نیاز فقط خواندنی', default=False,
                                          help='اگر این گزینه فعال باشد، فیلد تاریخ نیاز در لاین‌های درخواست فقط خواندنی خواهد بود')
    active = fields.Boolean(default=True)
    color_tag = fields.Selection([
        ('danger', 'قرمز'),
        ('success', 'سبز'),
        ('info', 'آبی روشن'),
        ('warning', 'نارنجی'),
        ('muted', 'خاکستری'),
        ('primary', 'آبی'),
        ('secondary', 'خاکستری تیره'),
    ], string='رنگ نمایش', default='', required=True)