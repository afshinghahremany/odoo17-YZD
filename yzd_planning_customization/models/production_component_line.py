from odoo import models, fields, api

class ProductionComponentLine(models.Model):
    _name = 'production.component.line'
    _description = 'Production Planning Component Line'

    planning_id = fields.Many2one('production.planning', string='Production Planning', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='کالا', required=True)
    required_qty = fields.Float(string='مورد نیاز', readonly=True, compute='_compute_all')
    transit_stock = fields.Float(string='موجودی در راه', readonly=True, compute='_compute_transit_stock')
    factory_stock = fields.Float(string='موجودی کارخانه', readonly=True, compute='_compute_all')
    supplier_stock = fields.Float(string='موجودی نزد تامین کننده', readonly=True, compute='_compute_all')
    factory_safety = fields.Float(string='احتیاطی کارخانه', readonly=True, compute='_compute_all')
    vendor_safety = fields.Float(string='احتیاطی تامین کننده', readonly=True, compute='_compute_all')
    shortage_qty = fields.Float(string='کسری مواد', readonly=True, compute='_compute_all')
    purchase_qty = fields.Float(string='خرید مورد نیاز', readonly=True, compute='_compute_all')
    document_qty = fields.Float(string='مقدار سند', default=0.0)
    needed_document_qty = fields.Float(string='کسری / مازاد', readonly=True, compute='_compute_all')
    state = fields.Selection(related='planning_id.state', string='وضعیت', store=True)
    @api.depends('planning_id.bom_line_ids', 'planning_id.work_days', 'product_id', 'document_qty')
    def _compute_all(self):
        for rec in self:
            # محاسبه مقدار مورد نیاز (required_qty)
            required_qty = 0
            if rec.planning_id and rec.product_id:
                for bom_line in rec.planning_id.bom_line_ids:
                    bom = bom_line.bom_id
                    produced_qty = bom_line.produced_qty
                    if bom:
                        for component in bom.bom_line_ids:
                            # واکشی مواد اولیه به صورت درختی
                            required_qty += rec._get_required_qty_recursive(component, produced_qty, rec.product_id)
            rec.required_qty = required_qty

            # موجودی کارخانه (internal, بدون تامین‌کننده)
            internal_locations = rec.env['stock.location'].search([('usage', '=', 'internal'), ('yzd_supplier_partner_id', '=', False)])
            rec.factory_stock = round(sum(
                rec.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', 'in', internal_locations.ids)
                ]).mapped('quantity')
            )/1000, 2)

            # موجودی نزد تامین‌کننده (internal, با تامین‌کننده)
            supplier_locations = rec.env['stock.location'].search([('usage', '=', 'internal'), ('yzd_supplier_partner_id', '!=', False)])
            rec.supplier_stock = round(sum(
                rec.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', 'in', supplier_locations.ids)
                ]).mapped('quantity')
            )/1000, 2)-rec.transit_stock

            # احتیاطی کارخانه
            work_days = rec.planning_id.work_days or 1
            factory_lead = rec.product_id.product_tmpl_id.factory_lead_time or 0
            rec.factory_safety = (rec.required_qty / work_days) * factory_lead if work_days and factory_lead else 0

            # احتیاطی تامین‌کننده
            vendor_lead = rec.product_id.product_tmpl_id.vendor_lead_time or 0
            rec.vendor_safety = (rec.required_qty / work_days) * vendor_lead if work_days and vendor_lead else 0

            # کسری مواد
            rec.shortage_qty = rec.required_qty - (rec.factory_stock + rec.supplier_stock + rec.transit_stock)
            if rec.shortage_qty < 0:
                rec.shortage_qty = 0

            # خرید مورد نیاز
            rec.purchase_qty = rec.shortage_qty + rec.factory_safety + rec.vendor_safety

            # کسری / مازاد
            rec.needed_document_qty = -(rec.document_qty - rec.factory_stock if rec.document_qty != 0 else 0) + rec.purchase_qty

    def _get_required_qty_recursive(self, component, produced_qty, target_product):
        """
        واکشی مقدار مورد نیاز از مواد اولیه به صورت بازگشتی (درختی)
        فقط مواد اولیه نهایی (برگ‌ها) را جمع می‌کند
        """
        if component.product_id == target_product:
            # اگر این کامپوننت همان کالای هدف است، مقدار را برگردان
            return produced_qty * component.product_qty / (component.bom_id.product_qty or 1)
        # اگر این کامپوننت خودش BOM دارد، مواد اولیه آن را واکشی کن
        bom = self.env['mrp.bom'].search([
            '|',
            ('product_id', '=', component.product_id.id),
            ('product_tmpl_id', '=', component.product_id.product_tmpl_id.id)
        ], limit=1)
        if bom and bom.bom_line_ids:
            total = 0
            for line in bom.bom_line_ids:
                total += self._get_required_qty_recursive(line, produced_qty * component.product_qty / (component.bom_id.product_qty or 1), target_product)
            return total
        return 0

    @api.depends('product_id')
    def _compute_transit_stock(self):
        for rec in self:
            if rec.product_id:
                # پیدا کردن انبارهای مبدا و مقصد
                vendor_locations = self.env['stock.location'].search([
                    ('usage', '=', 'internal'),
                    ('yzd_supplier_partner_id', '!=', False)
                ])
                internal_locations = self.env['stock.location'].search([
                    ('usage', '=', 'internal'),
                    ('yzd_supplier_partner_id', '=', False)
                ])

                # پیدا کردن اسناد انبار با شرایط گفته شده
                pickings = self.env['stock.picking'].search([
                    ('state', '=', 'draft'),
                    ('picking_type_code', '=', 'internal'),
                    ('location_id', 'in', vendor_locations.ids),
                    ('location_dest_id', 'in', internal_locations.ids),
                ])

                # جمع مقدار محصول مورد نظر در خطوط این اسناد
                qty_in_transit_kg = 0
                for picking in pickings:
                    for move in picking.move_ids_without_package:
                        if move.product_id.id == rec.product_id.id:
                            qty_in_transit_kg += move.product_uom_qty

                rec.transit_stock = round(qty_in_transit_kg / 1000, 2)
            else:
                rec.transit_stock = 0.0
