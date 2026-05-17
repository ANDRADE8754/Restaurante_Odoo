from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido a domicilio",
        copy=False,
        index=True,
        ondelete="set null",
    )
