from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _post_process(self):
        res = super()._post_process()

        for tx in self.filtered(lambda t: t.state == "pending" and t.operation != "validation"):
            manual_orders = tx.sale_order_ids.filtered(
                lambda so: so.website_id
                and so.state in ("draft", "sent")
                and so.website_payment_method in ("cash", "transfer")
            )
            if manual_orders:
                manual_orders.with_context(send_email=True).action_confirm()

        return res
