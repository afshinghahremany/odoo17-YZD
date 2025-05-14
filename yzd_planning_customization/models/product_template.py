from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    factory_lead_time = fields.Float(string='مدت زمان کارخانه (روز)')
    vendor_lead_time = fields.Float(string='مدت زمان تامین (روز)')