from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransportPlanning(models.Model):
    _name = 'transport.planning'
    _description = 'برنامه‌ریزی حمل'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='شماره حمل', readonly=True, default='New')
    state = fields.Selection([
        ('draft', 'پیش نویس'),
        ('under_review', 'در حال تایید'),
        ('approved', 'تایید'),
        ('cancelled', 'کنسل'),
    ], string='وضعیت', default='draft', tracking=True)
    start_date = fields.Date(string='تاریخ شروع', required=True)
    end_date = fields.Date(string='تاریخ پایان', required=True)
    return_reason = fields.Text(string='دلیل برگشت', tracking=True)
    line_ids = fields.One2many('transport.planning.line', 'planning_id', string='مواد مورد نیاز')
    purchase_request_line_count = fields.Integer(
        string="تعداد درخواست خرید",
        compute="_compute_purchase_request_line_count"
    )
    freight_orders_count = fields.Integer(
        string="تعداد سفارش حمل",
        compute="_compute_freight_orders_count"
    )   
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('transport.planning.seq') or 'New'
        return super().create(vals_list)

    @api.onchange('start_date', 'end_date')
    def _onchange_dates(self):
        if self.start_date and self.end_date:
            # حذف خطوط قبلی
            self.line_ids = [(5, 0, 0)]
            
            # جستجوی کالاهای مواد اولیه
            raw_material_products = self.env['product.product'].search([
                ('categ_id.is_raw_material', '=', True),
                ('active', '=', True)
            ])
            
            # ایجاد خطوط جدید برای هر کالا
            for product in raw_material_products:
                self.line_ids = [(0, 0, {
                    'product_id': product.id,
                    'tank_capacity': 0,
                    'required_factory_qty': 0,
                })]

    @api.depends('name')
    def _compute_freight_orders_count(self):
        for rec in self:
            rec.freight_orders_count = rec.env['freight.order'].search_count([('origin', '=', rec.name)])

    def action_view_freight_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Freight Orders',
            'res_model': 'freight.order',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],
            'context': {'search_default_origin': self.name},
            'target': 'current',
        }


    @api.depends('name')
    def _compute_purchase_request_line_count(self):
        for rec in self:
            rec.purchase_request_line_count = rec.env['purchase.request.line'].search_count([('origin', '=', rec.name)])

    def action_view_purchase_request_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Requests',
            'res_model': 'purchase.request.line',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],
            'context': {'search_default_origin': self.name},
            'target': 'current',
        }

    def action_send_for_approval(self):
        for rec in self:
            # بررسی اینکه حداقل یک ردیف مقدار required_factory_qty داشته باشد
            has_required_qty = any(
                line.required_factory_qty and line.required_factory_qty > 0
                for line in rec.line_ids
            )
            if not has_required_qty:
                raise ValidationError("لطفاً حداقل برای یک ردیف 'مقدار مورد نیاز کارخانه' را وارد کنید.")
            rec.state = 'under_review'

    def action_return(self):
        return {
            'name': 'دلیل برگشت',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.planning.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_planning_id': self.id,
            }
        }
    
    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec._create_purchase_requests()
            rec._create_freight_orders()


    def _create_freight_orders(self):
        FreightOrder = self.env['freight.order']
        FreightOrderLine = self.env['freight.order.line']
        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.qty_to_send and l.qty_to_send > 0):
                # پیدا کردن تامین کننده پیش‌فرض
                #default_shipper = self.env['res.partner'].search([('is_shipper', '=', True)], limit=1)
                #if not default_shipper:
                    #raise ValidationError("هیچ تامین کننده پیش‌فرضی یافت نشد. لطفاً یک تامین کننده با گزینه 'تامین کننده' فعال ایجاد کنید.")
                
                # پیدا کردن پارتنر کمپانی
                company_partner = self.env.company.partner_id
                
                fo = FreightOrder.create({
                    'origin': rec.name,
                    'order_date': fields.Date.today(),
                    'immediate': True,
                    #'shipper_id': default_shipper.id,
                    'consignee_id': company_partner.id,
                })
                # ایجاد خط سفارش حمل
                FreightOrderLine.create({
                    'order_id': fo.id,
                    'freight_origin': rec.name,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'quantity': line.qty_to_send*1000,
                })



    def _create_purchase_requests(self):
        PurchaseRequest = self.env['purchase.request']
        PurchaseRequestLine = self.env['purchase.request.line']
        for rec in self:
            # فقط خطوطی که کسری دارند
            lines_with_shortage = rec.line_ids.filtered(lambda l: l.qty_shortage > 0)
            if not lines_with_shortage:
                continue
            request_type = rec.env['purchase.request.type'].search([('name', '=', 'خرید استراتژیک')], limit=1)
            approver = request_type.approver_id.id if request_type else False
# ایجاد درخواست خرید
            pr = PurchaseRequest.create({
                'origin': rec.name,
                'date_start': fields.Date.today(),
                'request_type_id': request_type.id if request_type else False,  # اگر نوع خرید دارید
                'assigned_to': approver,
                'description': 'درخواست خرید اتوماتیک از برنامه ریزی حمل',
                'state': 'to_approve',
            })
            # ایجاد خطوط درخواست خرید
            for line in lines_with_shortage:
                PurchaseRequestLine.create({
                    'request_id': pr.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_qty': round(line.qty_shortage*1000, 0),  # مقدار کسری
                    'description': line.product_id.display_name,
                    'origin': rec.name,
                    'date_required': fields.Date.context_today(rec),
                })
            # پیام در چتر
            rec.message_post(body=_("درخواست خرید برای مواد دارای کسری ایجاد شد."))

class TransportPlanningLine(models.Model):
    _name = 'transport.planning.line'
    _description = 'خط مواد مورد نیاز حمل'

    planning_id = fields.Many2one('transport.planning', string='برنامه‌ریزی حمل', ondelete='cascade')
    state = fields.Selection(related='planning_id.state', string='وضعیت', store=True)
    product_id = fields.Many2one(
        'product.product', string='کالا',
        domain="[('categ_id.is_raw_material','=',True), ('active','=',True)]",
        required=True
    )
    factory_stock = fields.Float(string='در کارخانه', compute='_compute_stock', store=True)
    transit_stock = fields.Float(string='موجودی در راه', readonly=True, compute='_compute_transit_stock')
    supplier_stock = fields.Float(string='نزد تامین کننده', compute='_compute_stock', store=True)
    tank_capacity = fields.Integer(string='ظرفیت تانک', required=True)
    empty_capacity = fields.Integer(string='ظرفیت خالی', compute='_compute_empty_capacity', store=True)
    required_factory_qty = fields.Integer(string='مورد نیاز', required=True)
    qty_to_send = fields.Float(
        string='مقدار حمل',
        tracking=True,
        compute='_compute_qty_to_send',
        store=True
    )
    qty_shortage = fields.Integer(string='مقدار خرید', compute='_compute_qty_shortage', store=True)
    description = fields.Char(
        string='توضیحات',
        compute='_compute_description',
        store=True,
        sanitize=False
    )
    
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

    @api.depends('required_factory_qty', 'factory_stock', 'supplier_stock')
    def _compute_qty_shortage(self):
        for rec in self:
            rec.qty_shortage = rec.required_factory_qty - rec.factory_stock - rec.supplier_stock

    @api.depends('product_id')
    def _compute_stock(self):
        for rec in self:
            if rec.product_id:
                # محاسبه موجودی کارخانه
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id.usage', '=', 'internal'),
                    ('location_id.yzd_supplier_partner_id', '=', False)
                ], limit=1)
                rec.factory_stock = round(stock_quant.quantity/1000, 2) if stock_quant else 0.0

                # محاسبه موجودی تامین کننده
                supplier_stock = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id.usage', '=', 'internal'),
                    ('location_id.yzd_supplier_partner_id', '!=', False)
                ], limit=1)
                rec.supplier_stock = round(supplier_stock.quantity/1000, 2)-rec.transit_stock if supplier_stock else 0.0
            else:
                rec.factory_stock = 0.0
                rec.supplier_stock = 0.0

    @api.constrains('tank_capacity', 'factory_stock')
    def _check_tank_capacity(self):
        for rec in self:
            if rec.tank_capacity < rec.factory_stock:
                raise ValidationError('ظرفیت تانک باید بزرگتر یا مساوی موجودی کارخانه باشد.')

    @api.depends('tank_capacity', 'factory_stock')
    def _compute_empty_capacity(self):
        for rec in self:
            rec.empty_capacity = (rec.tank_capacity or 0) - (rec.factory_stock or 0 if rec.tank_capacity > 0 else 0)

    @api.depends('required_factory_qty', 'supplier_stock')
    def _compute_description(self):
        for rec in self:
            rq = rec.required_factory_qty or 0
            ss = rec.supplier_stock or 0
            if rq == 0:
                rec.description = ''
            elif rq > ss:
                rec.description = "تامین و حمل فوری" if ss == 0 else "حمل و تامین فوری"
            else:
                rec.description = '🔴 حمل فوری'

    @api.depends('required_factory_qty', 'supplier_stock')
    def _compute_qty_to_send(self):
        for rec in self:
            rec.qty_to_send = min(rec.required_factory_qty, rec.supplier_stock)

class TransportPlanningReturnWizard(models.TransientModel):
    _name = 'transport.planning.return.wizard'
    _description = 'ویزارد برگشت برنامه‌ریزی حمل'

    planning_id = fields.Many2one('transport.planning', string='برنامه‌ریزی حمل', required=True)
    return_reason = fields.Text(string='دلیل برگشت', required=True)

    def action_confirm_return(self):
        self.planning_id.write({
            'state': 'draft',
            'return_reason': self.return_reason
        })
        self.planning_id.message_post(
            body=_('برگشت به پیش نویس با دلیل: %s') % self.return_reason
        )
        return True
    


