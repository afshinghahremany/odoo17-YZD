from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import ValidationError

class ProductionPlanning(models.Model):
    _name = 'production.planning'
    _description = 'Production Planning'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plan Number', readonly=True, default='New', tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    operation_id = fields.Many2one(
        'resource.resource',
        string='Operation',
        required=True,
        domain=[('resource_type', '=', 'material')],
        tracking=True
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    work_days = fields.Integer(string='Work Days', compute='_compute_work_days', store=True)
    production_capacity = fields.Float(string='Production Capacity (Tons)', compute='_compute_capacity', store=True)
    bom_line_ids = fields.One2many('production.bom.line', 'planning_id', string='BOM Lines')
    component_line_ids = fields.One2many('production.component.line', 'planning_id', string='مواد اولیه مورد نیاز')
    purchase_request_line_count = fields.Integer(
        string="تعداد درخواست خرید",
        compute="_compute_purchase_request_line_count"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('x_production_planning') or 'New'
        return super().create(vals_list)

    @api.depends('start_date', 'end_date')
    def _compute_work_days(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.work_days = (fields.Date.from_string(rec.end_date) - fields.Date.from_string(rec.start_date)).days + 1
            else:
                rec.work_days = 0

    @api.depends('start_date', 'end_date')
    def _compute_capacity(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.production_capacity = self._calculate_capacity(rec.start_date, rec.end_date)
            else:
                rec.production_capacity = 0.0

    def _calculate_capacity(self, start, end):
        # محاسبه ظرفیت تولید بر اساس ماه شمسی و تعداد روزها
        # فرض: ظرفیت خط تولید ماهانه از تنظیمات خوانده می‌شود
        capacity_per_month = self.env.user.company_id.production_line_capacity or 0.0
        # محاسبه تعداد روز ماه شمسی
        start_date = fields.Date.from_string(start)
        month = int(start_date.strftime('%m'))
        year = int(start_date.strftime('%Y'))
        if month <= 6:
            days_in_month = 31
        elif month <= 11:
            days_in_month = 30
        else:
            # اسفند
            days_in_month = 29  # برای سادگی، کبیسه را لحاظ نکردیم
        # ظرفیت روزانه
        daily_capacity = capacity_per_month / days_in_month if days_in_month else 0
        work_days = self._calculate_work_days(start, end)
        return round(daily_capacity * work_days, 2)

    @api.constrains('bom_line_ids')
    def _check_total_percent(self):
        for rec in self:
            if rec.bom_line_ids:  # فقط اگر خطی وجود داشت، چک کن
                total = sum(line.percent for line in rec.bom_line_ids)
                if round(total, 2) != 100.0 and len(rec.bom_line_ids) > 0:
                    raise ValidationError("مجموع درصدهای همه خطوط باید دقیقاً 100 باشد. مجموع فعلی: %s" % total)

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id and not self.bom_line_ids:
            boms = self.env['mrp.bom'].search([('operation_id', '=', self.operation_id.id)])
            lines = []
            for bom in boms:
                lines.append((0, 0, {'bom_id': bom.id, 'percent': 0}))
            self.bom_line_ids = lines

    def _calculate_work_days(self, start, end):
        """محاسبه تعداد روز کاری بین دو تاریخ (شامل هر دو تاریخ)"""
        if start and end:
            return (fields.Date.from_string(end) - fields.Date.from_string(start)).days + 1
        return 0

    def action_calculate_components(self):
        """ایجاد یا به‌روزرسانی خطوط مواد اولیه مورد نیاز بر اساس BOMها و مقدار تولید"""
        for rec in self:
            # حذف خطوط قبلی
            rec.component_line_ids.unlink()
            # دیکشنری برای جمع مقدار هر کالا
            component_dict = {}
            for bom_line in rec.bom_line_ids:
                bom = bom_line.bom_id
                produced_qty = bom_line.produced_qty
                if bom:
                    for component in bom.bom_line_ids:
                        rec._get_leaf_components(component, produced_qty, component_dict)
            # ساخت خطوط جدید
            for vals in component_dict.values():
                vals['planning_id'] = rec.id
                rec.env['production.component.line'].create(vals)

    def _get_leaf_components(self, component, produced_qty, component_dict, visited=None):
        """واکشی مواد اولیه نهایی (برگ‌ها) به صورت بازگشتی"""
        if visited is None:
            visited = set()
        # جلوگیری از حلقه بی‌نهایت
        if component.product_id.id in visited:
            return
        visited.add(component.product_id.id)
        # آیا این کالا خودش BOM دارد؟
        bom = self.env['mrp.bom'].search([
            '|',
            ('product_id', '=', component.product_id.id),
            ('product_tmpl_id', '=', component.product_id.product_tmpl_id.id)
        ], limit=1)
        if bom and bom.bom_line_ids:
            for line in bom.bom_line_ids:
                self._get_leaf_components(
                    line,
                    produced_qty * component.product_qty / (component.bom_id.product_qty or 1),
                    component_dict,
                    visited
                )
        else:
            # اگر BOM ندارد، به عنوان ماده اولیه نهایی اضافه کن
            key = component.product_id.id
            qty = produced_qty * component.product_qty / (component.bom_id.product_qty or 1)
            if key in component_dict:
                component_dict[key]['required_qty'] += qty
            else:
                component_dict[key] = {
                    'product_id': component.product_id.id,
                    'required_qty': qty,
                    'document_qty': 0.0,  # مقدار پیش‌فرض
                }

    def action_send_for_review(self):
        for rec in self:
            rec.state = 'under_review'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            # فقط لاین‌هایی که کسری/مازاد آنها مثبت است
            lines_to_request = rec.component_line_ids.filtered(lambda l: l.needed_document_qty > 0)
            if not lines_to_request:
                continue

            # واکشی نوع درخواست (Purchase Request Type) با نام "برنامه ریزی تولید"
            request_type = rec.env['purchase.request.type'].search([('name', '=', 'برنامه ریزی تولید')], limit=1)
            approver = request_type.approver_id.id if request_type else False

            # ساخت درخواست خرید
            purchase_request = rec.env['purchase.request'].create({
                'requested_by': rec.env.user.id,
                'request_type_id': request_type.id if request_type else False,
                'assigned_to': approver,
                'origin': rec.name,
                'description': 'درخواست خرید اتوماتیک از برنامه ریزی تولید',
                'state': 'to_approve',
            })

            # ساخت خطوط درخواست خرید
            for line in lines_to_request:
                rec.env['purchase.request.line'].create({
                    'request_id': purchase_request.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_qty': round(line.needed_document_qty*1000, 0),
                    'origin': rec.name,
                    'date_required': fields.Date.context_today(rec),
                })

            # ایجاد رکورد جدید در planning.slot
            rec.env['planning.slot'].create({
                'resource_id': rec.operation_id.id,
                'start_datetime': rec.start_date,
                'end_datetime': rec.end_date,
            })

    def action_back_to_draft(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'production.planning.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
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

