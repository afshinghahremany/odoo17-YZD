# Copyright (C) 2021 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from odoo import _, api, exceptions, fields, models


class AccountVoucherWizardPurchase(models.TransientModel):
    _name = "account.voucher.wizard.purchase"
    _description = "Account Voucher Wizard Purchase"

    order_id = fields.Many2one("purchase.order", required=True)
    journal_id = fields.Many2one(
        "account.journal",
        "Journal",
        required=True,
        domain=[("type", "in", ("bank", "cash"))],
    )
    journal_currency_id = fields.Many2one(
        "res.currency",
        "Journal Currency",
        store=True,
        readonly=False,
        compute="_compute_get_journal_currency",
    )
    currency_id = fields.Many2one("res.currency", "Currency", readonly=True)
    amount_total = fields.Monetary(readonly=True)
    amount_advance = fields.Monetary(
        "Amount advanced", required=True, currency_field="journal_currency_id"
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    currency_amount = fields.Monetary(
        "Curr. amount",
        readonly=True,
        currency_field="currency_id",
        compute="_compute_currency_amount",
        store=True,
    )
    payment_ref = fields.Char("Ref.")
    payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Payment Method",
        readonly=False,
        store=True,
        compute="_compute_payment_method_line_id",
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )
    available_payment_method_line_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        compute="_compute_available_payment_method_line_ids",
    )
    automatic_payment = fields.Boolean(
        string="اتوماتیک کردن ثبت پرداخت",
        default=False,
        help="اگر فعال باشد، پرداخت‌ها برای این نوع خرید به صورت اتوماتیک و بدون باز شدن فرم ویزارد ثبت می‌شوند."
    )

    @api.depends("journal_id")
    def _compute_get_journal_currency(self):
        for wzd in self:
            wzd.journal_currency_id = (
                wzd.journal_id.currency_id.id or self.env.user.company_id.currency_id.id
            )

    @api.depends("journal_id")
    def _compute_payment_method_line_id(self):
        for wizard in self:
            if wizard.journal_id:
                available_payment_method_lines = (
                    wizard.journal_id._get_available_payment_method_lines("outbound")
                )
            else:
                available_payment_method_lines = False
            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[
                    0
                ]._origin
            else:
                wizard.payment_method_line_id = False

    @api.depends("journal_id")
    def _compute_available_payment_method_line_ids(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_method_line_ids = (
                    wizard.journal_id._get_available_payment_method_lines("outbound")
                )
            else:
                wizard.available_payment_method_line_ids = False

    @api.constrains("amount_advance")
    def check_amount(self):
        if self.journal_currency_id.compare_amounts(self.amount_advance, 0.0) <= 0:
            raise exceptions.ValidationError(_("Amount of advance must be positive."))
        if self.env.context.get("active_id", False):
            if (
                self.currency_id.compare_amounts(
                    self.currency_amount, self.order_id.amount_residual
                )
                > 0
            ):
                raise exceptions.ValidationError(
                    _("Amount of advance is greater than residual amount on purchase")
                )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        purchase_ids = self.env.context.get("active_ids", [])
        if not purchase_ids:
            return res
        purchase_id = fields.first(purchase_ids)
        purchase = self.env["purchase.order"].browse(purchase_id)
        if "amount_total" in fields_list:
            res.update(
                {
                    "order_id": purchase.id,
                    "amount_total": purchase.amount_residual,
                    "currency_id": purchase.currency_id.id,
                }
            )
        no_currency_journal_domain = [
            ("type", "in", ("bank", "cash")),
            ("company_id", "=", purchase.company_id.id),
            ("outbound_payment_method_line_ids", "!=", False),
        ]
        journal_domain = no_currency_journal_domain
        if purchase.company_id.currency_id != purchase.currency_id:
            journal_domain.append(
                ("currency_id", "=", purchase.currency_id.id),
            )
        journal = self.env["account.journal"].search(
            journal_domain,
            limit=1,
        )
        if not journal:
            journal = self.env["account.journal"].search(
                no_currency_journal_domain,
                limit=1,
            )
        res["journal_id"] = journal.id
        return res

    @api.depends("journal_id", "date", "amount_advance", "journal_currency_id")
    def _compute_currency_amount(self):
        for rec in self:
            amount_advance = rec.amount_advance or 0.0
            if rec.journal_currency_id and rec.journal_currency_id != rec.currency_id:
                amount_advance = rec.journal_currency_id._convert(
                    amount_advance,
                    rec.currency_id,
                    rec.order_id.company_id,
                    rec.date or fields.Date.today(),
                )
            rec.currency_amount = amount_advance

    def _prepare_payment_vals(self, purchase):
        partner_id = purchase.partner_id.commercial_partner_id.id
        return {
            "purchase_id": purchase.id,
            "date": self.date,
            "amount": self.amount_advance,
            "payment_type": "outbound",
            "partner_type": "supplier",
            "ref": self.payment_ref or purchase.name,
            "journal_id": self.journal_id.id,
            "currency_id": self.journal_currency_id.id,
            "partner_id": partner_id,
            "payment_method_line_id": self.payment_method_line_id.id,
        }

     
    def make_advance_payment(self):
        self.ensure_one()
        payment_obj = self.env["account.payment"]

    # همیشه از فیلد order_id استفاده کن (چه ویزارد دستی باشد چه اتوماتیک)
        purchase = self.order_id

        payment_vals = self._prepare_payment_vals(purchase)
        payment = payment_obj.create(payment_vals)

    # اگر می‌خواهی پرداخت بلافاصله ثبت (post) شود، این خط را فعال کن:
    # payment.action_post()

        return {
            "type": "ir.actions.act_window_close",
        }


    