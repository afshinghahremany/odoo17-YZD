from xml.dom import ValidationErr
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class StockLocation(models.Model):
    _inherit = 'stock.location'
    yzd_capacity_nominal = fields.Float(string='Nominal Capacity (tons)', help="Maximum storage capacity in tons.")
    yzd_capacity_actual = fields.Float(string='Actual Capacity (tons)', help="Current actual stored amount in tons.")
    yzd_supplier_partner_id = fields.Many2one(
        'res.partner',
        string='Supplier Partner',
        domain="[('active', '=', True)]"
    )
    @api.depends('usage')
    def _compute_supplier_partner(self):
        """Compute supplier partner based on usage"""
        for rec in self:
            if rec.usage != 'supplier':
                rec.yzd_supplier_partner_id = False
    @api.onchange('usage')
    def _onchange_usage(self):
        """Clear supplier partner when location type is not supplier"""
        if self.usage != 'supplier':
            self.yzd_supplier_partner_id = False
    @api.constrains('usage', 'yzd_supplier_partner_id')
    def _check_supplier_partner_required(self):
        for rec in self:
            if rec.usage == 'supplier' and not rec.yzd_supplier_partner_id:
                raise ValidationError(_('لطفاً برای انبار یک تامین‌کننده انتخاب کنید.'))
            elif rec.usage != 'supplier' and rec.yzd_supplier_partner_id:
                rec.yzd_supplier_partner_id = False
    @api.model
    def _get_supplier_partner_ids(self):
        return self.search([('usage', '=', 'supplier'), ('yzd_supplier_partner_id', '!=', False)]).mapped('yzd_supplier_partner_id').ids
    supplier_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_supplier_partner_ids',
        string='Assigned Supplier Partners'
    )
    @api.depends('usage', 'yzd_supplier_partner_id')
    def _compute_supplier_partner_ids(self):
        partner_ids = self._get_supplier_partner_ids()
        for rec in self:
            rec.supplier_partner_ids = [(6, 0, partner_ids)]
    def write(self, vals):
        """Override write to clear supplier partner when usage changes"""
        if 'usage' in vals and vals['usage'] != 'supplier':
            vals['yzd_supplier_partner_id'] = False
        return super().write(vals)
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to prevent setting supplier partner for non-supplier locations"""
        for vals in vals_list:
            if 'yzd_supplier_partner_id' in vals and vals.get('usage') != 'supplier':
                raise UserError(_('You cannot set supplier partner for non-supplier locations.'))
        return super().create(vals_list)
    @api.depends('usage')
    def _compute_supplier_domain(self):
        """Compute domain for supplier partner field"""
        for rec in self:
            if rec.usage != 'supplier':
                rec.yzd_supplier_partner_id = False
                return [('id', '=', False)]  # Empty domain when not supplier
            return [('active', '=', True)]   # Normal domain for suppliers
    def action_edit_supplier(self):
        """Custom method to edit supplier partner"""
        self.ensure_one()
        if self.usage != 'supplier':
            raise UserError(_('You can only edit supplier partner for supplier locations.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'edit_supplier': True},
        }