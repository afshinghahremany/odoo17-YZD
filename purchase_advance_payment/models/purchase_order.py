# Copyright (C) 2021 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)
from asyncio import exceptions
from odoo import api, fields, models
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    account_payment_ids = fields.One2many(
        "account.payment", "purchase_id", string="Pay purchase advanced", readonly=True
    )
    amount_residual = fields.Float(
        "Residual amount",
        readonly=True,
        compute="_compute_purchase_advance_payment",
        store=True,
    )
    payment_line_ids = fields.Many2many(
        "account.move.line",
        string="Payment move lines",
        compute="_compute_purchase_advance_payment",
        store=True,
    )
    advance_payment_status = fields.Selection(
        selection=[
            ("not_paid", "Not Paid"),
            ("paid", "Paid"),
            ("partial", "Partially Paid"),
        ],
        store=True,
        readonly=True,
        copy=False,
        tracking=True,
        compute="_compute_purchase_advance_payment",
    )

    @api.depends(
        "currency_id",
        "company_id",
        "amount_total",
        "account_payment_ids",
        "account_payment_ids.state",
        "account_payment_ids.move_id",
        "account_payment_ids.move_id.line_ids",
        "account_payment_ids.move_id.line_ids.date",
        "account_payment_ids.move_id.line_ids.debit",
        "account_payment_ids.move_id.line_ids.credit",
        "account_payment_ids.move_id.line_ids.currency_id",
        "account_payment_ids.move_id.line_ids.amount_currency",
        "order_line.invoice_lines.move_id",
        "order_line.invoice_lines.move_id.amount_total",
        "order_line.invoice_lines.move_id.amount_residual",
    )
    def _compute_purchase_advance_payment(self):
        for order in self:
            mls = order.account_payment_ids.mapped("move_id.line_ids").filtered(
                lambda x: x.account_id.account_type == "liability_payable"
                and x.parent_state != "cancel"
            )
            advance_amount = 0.0
            for line in mls:
                line_currency = line.currency_id or line.company_id.currency_id
                # Exclude reconciled pre-payments amount because once reconciled
                # the pre-payment will reduce bill residual amount like any
                # other payment.
                line_amount = (
                    line.amount_residual_currency
                    if line.currency_id
                    else line.amount_residual
                )
                if line_currency != order.currency_id:
                    advance_amount += line.currency_id._convert(
                        line_amount,
                        order.currency_id,
                        order.company_id,
                        line.date or fields.Date.today(),
                    )
                else:
                    advance_amount += line_amount
            # Consider payments in related invoices.
            invoice_paid_amount = 0.0
            for inv in order.invoice_ids:
                invoice_paid_amount += inv.amount_total - inv.amount_residual
            amount_residual = order.amount_total - advance_amount - invoice_paid_amount
            payment_state = "not_paid"
            if mls or not order.currency_id.is_zero(invoice_paid_amount):
                has_due_amount = float_compare(
                    amount_residual, 0.0, precision_rounding=order.currency_id.rounding
                )
                if has_due_amount <= 0:
                    payment_state = "paid"
                elif has_due_amount > 0:
                    payment_state = "partial"
            order.payment_line_ids = mls
            order.amount_residual = amount_residual
            order.advance_payment_status = payment_state
    def action_auto_advance_payment(self):
        self.ensure_one()
    # اگر نوع سفارش خرید و فیلد اتوماتیک فعال بود
        if self.order_type and getattr(self.order_type, 'automatic_payment', False):
            wizard = self.env['account.voucher.wizard.purchase']
            total_amount = self.amount_total  # یا self.amount_total بسته به نیاز پروژه
            today = fields.Date.context_today(self)
            journal = self.env['account.journal'].search([
                ("type", "in", ("bank", "cash")),
                ("company_id", "=", self.company_id.id),
                ("outbound_payment_method_line_ids", "!=", False),
            ], limit=1)
            if not journal:
                raise exceptions.UserError("هیچ ژورنال بانکی/نقدی برای پرداخت پیدا نشد!")

            if self.payment_term_id and self.payment_term_id.line_ids:
                for line in self.payment_term_id.line_ids:
                    if line.value == 'percent':
                        percent = line.value_amount / 100.0
                        amount = total_amount * percent
                    elif line.value == 'balance':
                        amount = total_amount
                    else:
                        continue

                    if amount <= 0:
                        continue  # از ثبت پرداخت با مبلغ صفر یا منفی جلوگیری می‌کند

   # اگر واحد پول IRR بود، فقط قسمت صحیح مبلغ را لحاظ کن
                    if self.currency_id.name == 'IRR':
                        amount = int(amount)
                        
                    nb_days = getattr(line, 'nb_days', 0) or 0
                    pay_date = fields.Date.add(today, days=nb_days)
                    payment_vals = {
                        "order_id": self.id,
                        "journal_id": journal.id,
                        "amount_advance": amount,
                        "date": pay_date,
                        "currency_id": self.currency_id.id,
                    }
                    wizard.create(payment_vals).make_advance_payment()
                    if line.value == 'balance':
                        break
            else:
            # اگر Payment Term نبود، کل مبلغ را پرداخت کن
                payment_vals = {
                    "order_id": self.id,
                    "journal_id": journal.id,
                    "amount_advance": total_amount,
                    "date": today,
                    "currency_id": self.currency_id.id,
                }
                wizard.create(payment_vals).make_advance_payment()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "پرداخت اتوماتیک انجام شد",
                    "type": "success",
                    "sticky": False,
                },
            }
    # اگر اتوماتیک نبود، ویزارد باز شود (رفتار پیش‌فرض)
        return self.env.ref('purchase_advance_payment.action_view_account_voucher_wizard').read()[0]