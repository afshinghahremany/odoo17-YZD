from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductionBomLine(models.Model):
    _name = 'production.bom.line'
    _description = 'Production BOM Line'

    planning_id = fields.Many2one('production.planning', string='Production Planning', ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BOM', required=True)
    product_tmpl_id = fields.Many2one(related='bom_id.product_tmpl_id', string='Product', store=True, readonly=True)
    code = fields.Char(related='bom_id.code', string='Code', store=True, readonly=True)
    percent = fields.Float(string='Percent', digits=(5,2), required=True)
    produced_qty = fields.Float(string='Produced Quantity', digits=(16,2), compute='_compute_produced_qty', store=True, readonly=True)
    state = fields.Selection(related='planning_id.state', string='وضعیت', store=True)
    @api.depends('percent', 'planning_id.production_capacity')
    def _compute_produced_qty(self):
        for line in self:
            if line.percent and line.planning_id.production_capacity:
                line.produced_qty = round(
                    (line.percent / 100.0) * line.planning_id.production_capacity, 2
                )
            else:
                line.produced_qty = 0.0

    @api.constrains('percent')
    def _check_percent(self):
        for line in self:
            if line.percent < 0 or line.percent > 100:
                raise ValidationError("درصد باید بین 0 تا 100 باشد.")
