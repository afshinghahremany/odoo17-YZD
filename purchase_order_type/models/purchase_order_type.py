# Copyright (C) 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PurchaseOrderType(models.Model):
    #_inherit = "purchase.order"
    _name = "purchase.order.type"
    _description = "Type of purchase order"
    _order = "sequence"
    # فیلدها و متدهای جدیدت را اینجا اضافه کن
    current_stage_id = fields.Many2one(
        'purchase.order.type.stage',
        string='Current Stage',
        readonly=True,
        copy=False
    )

    def action_next_stage(self):
        self.ensure_one()
        stage = self.current_stage_id
        if not stage:
            return
        # ثبت لاگ
        self.env['purchase.order.stage.log'].create({
            'order_id': self.id,
            'stage_id': stage.id,
            'user_id': self.env.user.id,
            'date': fields.Datetime.now(),
        })
        # ثبت پیام در چتروم سفارش خرید
        self.message_post(
            body=f"مرحله '{stage.name}' توسط {self.env.user.display_name} در تاریخ {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ثبت شد.",
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        # پیدا کردن مرحله بعدی
        stages = self.order_type.stage_ids.sorted('sequence')
        next_stage = False
        found = False
        for s in stages:
            if found:
                next_stage = s
                break
            if s.id == stage.id:
                found = True
        self.current_stage_id = next_stage.id if next_stage else False

    @api.model
    def _get_domain_sequence_id(self):
        seq_type = self.env.ref("purchase.seq_purchase_order")
        return [
            ("code", "=", seq_type.code),
            ("company_id", "in", [False, self.env.company.id]),
        ]

    @api.model
    def _default_sequence_id(self):
        seq_type = self.env.ref("purchase.seq_purchase_order")
        return seq_type.id

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Entry Sequence",
        copy=False,
        domain=lambda self: self._get_domain_sequence_id(),
        default=lambda self: self._default_sequence_id(),
        required=True,
    )
    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term", string="Payment Terms"
    )
    incoterm_id = fields.Many2one(comodel_name="account.incoterms", string="Incoterm")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    automatic_payment = fields.Boolean(
        string="اتوماتیک کردن ثبت پرداخت",
        default=False,
        help="اگر فعال باشد، پرداخت‌ها برای این نوع خرید به صورت اتوماتیک و بدون باز شدن فرم ویزارد ثبت می‌شوند."
    )
    stage_ids = fields.One2many('purchase.order.type.stage', 'order_type_id', string='Stages')