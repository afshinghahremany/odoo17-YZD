# Copyright 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    order_type = fields.Many2one(
        comodel_name="purchase.order.type",
        string="Type",
        ondelete="restrict",
        domain="[('company_id', 'in', [False, company_id])]",
        compute="_compute_partner_order_type",
        store=True,
        readonly=False,
    )
    current_stage_id = fields.Many2one(
        'purchase.order.type.stage',
        string='Current Stage',
        readonly=True,
        copy=False,
    )
    next_stage_name = fields.Char(
        string="Next Stage Name",
        compute="_compute_next_stage_name"
    )
    def action_next_stage(self):
        for order in self:
            if not order.order_type:
                continue  # اگر نوع سفارش مشخص نیست، کاری نکن

            # همه مراحل این نوع سفارش را بر اساس sequence مرتب کن
            stages = order.order_type.stage_ids.sorted('sequence')
            if not stages:
                continue

            # اگر هنوز مرحله‌ای انتخاب نشده، اولین مرحله را ست کن
            if not order.current_stage_id:
                order.current_stage_id = stages[0].id
                continue

            # مرحله فعلی را پیدا کن
            current_index = stages.ids.index(order.current_stage_id.id) if order.current_stage_id.id in stages.ids else -1
            # اگر مرحله بعدی وجود دارد، برو به آن
            if 0 <= current_index < len(stages) - 1:
                order.current_stage_id = stages[current_index + 1].id
            # اگر آخرین مرحله است، کاری نکن (یا می‌توانی پیغام بدهی)
    @api.depends('order_type', 'current_stage_id')
    def _compute_next_stage_name(self):
        for order in self:
            next_name = False
            if order.order_type:
                stages = order.order_type.stage_ids.sorted('sequence')
                if not order.current_stage_id and stages:
                    next_name = stages[0].name
                elif order.current_stage_id and stages:
                    current_index = stages.ids.index(order.current_stage_id.id) if order.current_stage_id.id in stages.ids else -1
                    if 0 <= current_index < len(stages) - 1:
                        next_name = stages[current_index + 1].name
            order.next_stage_name = next_name
    @api.onchange("partner_id")
    def onchange_partner_id(self):
        res = super().onchange_partner_id()
        purchase_type = (
            self.partner_id.purchase_type
            or self.partner_id.commercial_partner_id.purchase_type
        )
        if purchase_type:
            self.order_type = purchase_type
        return res

    @api.onchange("order_type")
    def onchange_order_type(self):
        for order in self:
            if order.order_type.payment_term_id:
                order.payment_term_id = order.order_type.payment_term_id.id
            else:
            # اگر در order_type خالی بود، از تامین‌کننده بگیر
                order.payment_term_id = order.partner_id.property_supplier_payment_term_id.id if order.partner_id and order.partner_id.property_supplier_payment_term_id else False
            if order.order_type.incoterm_id:
                order.incoterm_id = order.order_type.incoterm_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("name", "/") == "/" and values.get("order_type"):
                purchase_type = self.env["purchase.order.type"].browse(
                    values["order_type"]
                )
                if purchase_type.sequence_id:
                    values["name"] = purchase_type.sequence_id.next_by_id(
                        sequence_date=values.get("date_order")
                    )
        return super().create(vals_list)

    @api.constrains("company_id")
    def _check_po_type_company(self):
        if self.filtered(
            lambda r: r.order_type.company_id
            and r.company_id
            and r.order_type.company_id != r.company_id
        ):
            raise ValidationError(_("Document's company and type's company mismatch"))

    def _default_order_type(self):
        return self.env["purchase.order.type"].search(
            [("company_id", "in", [False, self.company_id.id])],
            limit=1,
        )

    @api.onchange("company_id")
    def _onchange_company(self):
        if not self.order_type or (
            self.order_type
            and self.order_type.company_id not in [self.company_id, False]
        ):
            self.order_type = self._default_order_type()

    @api.depends("partner_id")
    def _compute_partner_order_type(self):
        for record in self:
            if record.partner_id and not record.order_type:
                record.order_type = record.partner_id.purchase_type
            elif record.partner_id and record.order_type:
                record.order_type = record.order_type
            else:
                record.order_type = False
