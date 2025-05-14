from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    production_line_capacity = fields.Float(
        string='ظرفیت کل خط تولید'
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    production_line_capacity = fields.Float(
        string='ظرفیت کل خط تولید',
        related='company_id.production_line_capacity',
        readonly=False
    )
