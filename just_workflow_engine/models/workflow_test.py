# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError

class workflowtest(models.Model):
    _inherit = "crm.lead"
    _order = 'create_date desc'

    has_Standby = fields.Selection(selection=[('has', 'has Standby'), ('no', 'no Standby')], string='has_Standby')
    order_mode = fields.Selection(selection=[('sale', 'sale'), ('maintenance', 'maintenance')], string='order mode')
    field_inspection = fields.Boolean(string='Field testing')
    tower_maintenance = fields.Boolean(string='Tower maintenance')

    project_category = fields.Selection(selection=[('contract', 'contract'),
                                                   ('protocol', 'protocol'),
                                                   ('order', 'order')],
                                        string='Clue type', default='contract')