from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
from persiantools.jdatetime import JalaliDate
from datetime import datetime

_logger = logging.getLogger(__name__)

class PlanningSlotBomLine(models.Model):
    _name = 'planning.slot.bom.line'
    _description = 'Planning Slot BOM Lines'

    planning_slot_id = fields.Many2one('planning.slot', string='Planning Slot', required=True, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BOM', required=True)
    product_id = fields.Many2one(related='bom_id.product_id', string='Product', readonly=True, store=True)
    bom_code = fields.Char(related='bom_id.code', string='Reference', readonly=True, store=True)
    percentage = fields.Float(
        string='درصد',
        required=False,
        digits=(3, 2),  # دو رقم اعشار
    )
    production_amount = fields.Float(
        string='مقدار تولید',
        compute='_compute_production_amount',
        store=False,  # اگر می‌خواهی فقط نمایش باشد
    )

    @api.constrains('percentage')
    def _check_percentage(self):
        for record in self:
            if record.percentage is None or record.percentage < 0 or record.percentage > 100:
                raise ValidationError(_('درصد هر ردیف باید بین ۰ تا ۱۰۰ باشد.'))
            
    @api.depends('percentage', 'planning_slot_id.start_datetime', 'planning_slot_id.end_datetime')
    def _compute_production_amount(self):
        capacity = float(self.env['ir.config_parameter'].sudo().get_param('yzd.production_capacity', default=0))
        for line in self:
            start = line.planning_slot_id.start_datetime
            end = line.planning_slot_id.end_datetime
            if start and end:
                # تبدیل تاریخ میلادی به جلالی
                start_j = JalaliDate.to_jalali(start)
                end_j = JalaliDate.to_jalali(end)
                # تعداد روزهای بازه
                days = (end.date() - start.date()).days + 1
                # تعداد روزهای ماه جلالی
                if 1 <= start_j.month <= 6:
                    month_days = 31
                elif 7 <= start_j.month <= 11:
                    month_days = 30
                else:
                    # ماه ۱۲: کبیسه یا غیرکبیسه
                    if JalaliDate.isleap(start_j.year):
                        month_days = 30
                    else:
                        month_days = 29
                # ظرفیت متناسب با بازه
                slot_capacity = capacity * days / month_days
                line.production_amount = round((line.percentage or 0) * slot_capacity / 100, 2)
            else:
                line.production_amount = 0

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    resource_id = fields.Many2one(
        'resource.resource',
        string='Resource',
        domain=[('resource_type', '=', 'material')],
    )
    bom_line_ids = fields.One2many('planning.slot.bom.line', 'planning_slot_id', string='BOM Lines')
    component_line_ids = fields.One2many(
        'planning.slot.component.line', 'slot_id',
        string='مواد اولیه مورد نیاز'
    )

    @api.onchange('resource_id')
    def _onchange_resource_id(self):
        # واکشی BOMها یا داده‌های مرتبط با resource
        if self.resource_id:
            matching_boms = self.env['mrp.bom'].search([
                ('yzd_resource_id', '=', self.resource_id.id)
            ])
            self.bom_line_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'bom_id': bom.id,
                    'percentage': None,
                }) for bom in matching_boms
            ]

    @api.onchange('bom_line_ids.percentage', 'bom_line_ids.bom_id')
    def _onchange_bom_lines(self):
        # اعتبارسنجی درصدها
        if any(line.percentage is None or line.percentage < 0 or line.percentage > 100 for line in self.bom_line_ids):
            return {
                'warning': {
                    'title': 'خطا',
                    'message': 'درصد هر ردیف باید بین ۰ تا ۱۰۰ باشد.'
                }
            }
        total = sum(line.percentage or 0 for line in self.bom_line_ids)
        if round(total, 2) != 100.00:
            return {
                'warning': {
                    'title': 'خطا',
                    'message': f'جمع درصد همه محصولات باید دقیقاً ۱۰۰ باشد. مقدار فعلی: {total}'
                }
            }
        # اگر اعتبارسنجی اوکی بود، محاسبه مواد مورد نیاز را انجام بده
        self._calculate_requirements_onchange()

    def _calculate_requirements_onchange(self):
        component_dict = {}
        for bom_line in self.bom_line_ids:
            bom = bom_line.bom_id
            production_amount = bom_line.production_amount
            for component in bom.bom_line_ids:
                self._get_leaf_components(
                    component.product_id,
                    production_amount * component.product_qty / (bom.product_qty or 1),
                    component.product_uom_id,
                    component_dict
                )
        self.component_line_ids = [(5, 0, 0)]  # پاک کردن قبلی
        for vals in component_dict.values():
            # موجودی کارخانه (internal)
            internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
            qty_kg = sum(
                self.env['stock.quant'].search([
                    ('product_id', '=', vals['product_id']),
                    ('location_id', 'in', internal_locations.ids)
                ]).mapped('quantity')
            )
            vals['factory_stock'] = round(qty_kg / 1000, 2)

            # موجودی نزد تامین کننده (vendor)
            partner_id = vals.get('supplier_partner_id')
            if partner_id:
                domain = [
                    ('product_id', '=', vals['product_id']),
                    ('location_id', 'in', vendor_locations.ids),
                    ('owner_id', '=', partner_id)
                ]
            else:
                domain = [
                    ('product_id', '=', vals['product_id']),
                    ('location_id', 'in', vendor_locations.ids)
                ]
            vendor_locations = self.env['stock.location'].search([('usage', '=', 'supplier')])
            qty_vendor_kg = sum(self.env['stock.quant'].search(domain).mapped('quantity'))
            vals['supplier_stock'] = round(qty_vendor_kg / 1000, 2)

            # محاسبه موجودی در راه (transit_stock)
            # پیدا کردن انبارهای مبدا و مقصد
            vendor_locations = self.env['stock.location'].search([('usage', '=', 'supplier')])
            internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])

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
                    if move.product_id.id == vals['product_id']:
                        qty_in_transit_kg += move.product_uom_qty

            vals['transit_stock'] = round(qty_in_transit_kg / 1000, 2)

            self.env['planning.slot.component.line'].create(vals)

    def _get_leaf_components(self, product, qty, uom, bom_dict, visited=None):
        """
        واکشی مواد اولیه نهایی (برگ‌ها) برای یک محصول به صورت بازگشتی
        """
        if visited is None:
            visited = set()
        # جلوگیری از حلقه بی‌نهایت در BOMهای چرخشی
        if product.id in visited:
            return
        visited.add(product.id)
        # پیدا کردن BOM فعال برای این محصول (اول بر اساس product، بعد template)
        bom = self.env['mrp.bom'].search([
            '|',
            ('product_id', '=', product.id),
            ('product_tmpl_id', '=', product.product_tmpl_id.id)
        ], limit=1)
        if bom and bom.bom_line_ids:
            # اگر BOM دارد، مواد اولیه BOM را واکشی کن
            for line in bom.bom_line_ids:
                self._get_leaf_components(
                    line.product_id,
                    qty * line.product_qty / (bom.product_qty or 1),
                    line.product_uom_id,
                    bom_dict,
                    visited
                )
        else:
            # اگر BOM ندارد، به عنوان ماده اولیه نهایی اضافه کن
            key = (product.id, uom.id)
            if key in bom_dict:
                bom_dict[key]['required_qty'] += qty
            else:
                bom_dict[key] = {
                    'product_id': product.id,
                    'product_uom_id': uom.id,
                    'required_qty': round(qty, 2),
                    'slot_id': self.id,
                }

    def action_calculate_requirements(self):
        for slot in self:
            slot.check_total_percentage()
            component_dict = {}
            for bom_line in slot.bom_line_ids:
                bom = bom_line.bom_id
                production_amount = bom_line.production_amount
                for component in bom.bom_line_ids:
                    slot._get_leaf_components(
                        component.product_id,
                        production_amount * component.product_qty / (bom.product_qty or 1),
                        component.product_uom_id,
                        component_dict
                    )
            slot.component_line_ids.unlink()
            for vals in component_dict.values():
                # موجودی کارخانه (internal)
                internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
                qty_kg = sum(
                    self.env['stock.quant'].search([
                        ('product_id', '=', vals['product_id']),
                        ('location_id', 'in', internal_locations.ids)
                    ]).mapped('quantity')
                )
                vals['factory_stock'] = round(qty_kg / 1000, 2)

                # موجودی نزد تامین کننده (vendor)
                partner_id = vals.get('supplier_partner_id')
                vendor_locations = self.env['stock.location'].search([('usage', '=', 'supplier')])
                if partner_id:
                    domain = [
                        ('product_id', '=', vals['product_id']),
                        ('location_id', 'in', vendor_locations.ids),
                        ('owner_id', '=', partner_id)
                    ]
                else:
                    domain = [
                        ('product_id', '=', vals['product_id']),
                        ('location_id', 'in', vendor_locations.ids)
                    ]
                qty_vendor_kg = sum(self.env['stock.quant'].search(domain).mapped('quantity'))
                vals['supplier_stock'] = round(qty_vendor_kg / 1000, 2)

                # محاسبه موجودی در راه (transit_stock)
                # پیدا کردن انبارهای مبدا و مقصد
                vendor_locations = self.env['stock.location'].search([('usage', '=', 'supplier')])
                internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])

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
                        if move.product_id.id == vals['product_id']:
                            qty_in_transit_kg += move.product_uom_qty

                vals['transit_stock'] = round(qty_in_transit_kg / 1000, 2)

                # کم کردن مقدار در راه از نزد تامین کننده
                vals['supplier_stock'] = vals['supplier_stock'] - vals['transit_stock']

                self.env['planning.slot.component.line'].create(vals)

    @api.constrains('bom_line_ids')
    def _check_total_percentage(self):
        self.check_total_percentage()

    def check_total_percentage(self):
        for slot in self:
            if any(line.percentage is None for line in slot.bom_line_ids):
                raise ValidationError('لطفاً مقدار درصد همه محصولات را وارد کنید.')
            total = sum(line.percentage for line in slot.bom_line_ids)
            if round(total, 2) != 100.00:
                raise ValidationError(f'جمع درصد همه محصولات باید دقیقاً ۱۰۰ باشد. مقدار فعلی: {total}')

    # @api.constrains('start_datetime')
    # def _check_start_datetime_not_past(self):
    #     allow_past = self.env['ir.config_parameter'].sudo().get_param('yzd.planning_allow_past_start', 'False')
    #     allow_past = allow_past in ['1', 'True', 'true']
    #     for rec in self:
    #         if not allow_past and rec.start_datetime:
    #             if rec.start_datetime < fields.Datetime.now():
    #                 raise ValidationError(_('تاریخ شروع نمی‌تواند قبل از تاریخ جاری باشد.'))

class PlanningSlotComponentLine(models.Model):
    _name = 'planning.slot.component.line'
    _description = 'Planning Slot Component Line'

    slot_id = fields.Many2one('planning.slot', string='Planning Slot', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='ماده اولیه', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='واحد', required=True)
    required_qty = fields.Float(string='مورد نیاز', readonly=True)
    document_qty = fields.Float(string='مقدار سند')  # قابل ویرایش توسط کاربر

    factory_stock = fields.Float(string='در کارخانه', readonly=True)
    supplier_stock = fields.Float(string='نزد تامین کننده', readonly=True)
    transit_stock = fields.Float(string='در راه', readonly=True)

    shortage_qty = fields.Float(
        string='کسری مواد',
        readonly=True,
        compute='_compute_shortage_qty',
        store=True
    )
    purchase_qty = fields.Float(
        string='خرید مورد نیاز',
        readonly=True,
        compute='_compute_purchase_qty',
        store=True
    )
    transfer_qty = fields.Float(
        string='حمل مورد نیاز',
        readonly=True,
        compute='_compute_transfer_qty',
        store=True
    )

    @api.depends('product_id')
    def _compute_factory_stock(self):
        for rec in self:
            if rec.product_id:
                # واکشی همه انبارهای داخلی
                internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
                # جمع موجودی کالا در همه این انبارها
                qty = sum(
                    self.env['stock.quant'].search([
                        ('product_id', '=', rec.product_id.id),
                        ('location_id', 'in', internal_locations.ids)
                    ]).mapped('quantity')
                )
                rec.factory_stock = round(qty,2)
            else:
                rec.factory_stock = 0.0

    @api.depends('required_qty', 'factory_stock', 'supplier_stock', 'transit_stock')
    def _compute_shortage_qty(self):
        for rec in self:
            rec.shortage_qty = (
                (rec.required_qty or 0)
                - (rec.factory_stock or 0)
                - (rec.supplier_stock or 0)  # supplier_stock اینجا خودش transit_stock را کم دارد
            )

    @api.depends('shortage_qty', 'supplier_stock')
    def _compute_purchase_qty(self):
        for rec in self:
            rec.purchase_qty = (rec.shortage_qty or 0) - (rec.supplier_stock or 0)

    @api.depends('supplier_stock')
    def _compute_transfer_qty(self):
        for rec in self:
            rec.transfer_qty = rec.supplier_stock or 0

    