from odoo import models

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_accounting_data_for_valuation(self):
        journal_id, debit_account_id, credit_account_id, valuation_account_id = super()._get_accounting_data_for_valuation()
        # فقط برای رسید خرید (Receipt)
        if self.picking_id and self.picking_id.picking_type_code == 'incoming':
            dest_location = self.location_dest_id
            # اگر انبار مقصد تامین‌کننده دارد
            if dest_location.usage in ['internal', 'supplier'] and dest_location.yzd_supplier_partner_id:
                # حساب Inventory from Others روی کتگوری کالا
                consignment_account = self.product_id.categ_id.stock_others_trust_account_id
                if consignment_account:
                  #  debit_account_id = consignment_account.id
                    valuation_account_id = consignment_account.id
        return (journal_id, debit_account_id, credit_account_id, valuation_account_id)
