from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DeliveryCancelWizard(models.TransientModel):
    _name = "restaurant.delivery.cancel.wizard"
    _description = "Asistente de cancelación de pedido delivery"

    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido delivery",
        required=True,
        readonly=True,
    )
    delivery_state = fields.Selection(
        related="delivery_order_id.state",
        string="Estado del pedido",
        readonly=True,
    )
    cancel_reason = fields.Text(
        string="Motivo de cancelación",
        required=True,
    )
    notify_customer = fields.Boolean(
        string="Notificar al cliente",
        default=True,
    )

    def action_confirm_cancel(self):
        self.ensure_one()

        reason = (self.cancel_reason or "").strip()
        if not reason:
            raise UserError(_("Debe indicar un motivo de cancelación."))

        order = self.delivery_order_id
        if order.state not in ("preparing", "on_the_way"):
            raise UserError(
                _(
                    "Este pedido ya no está en un estado que requiera cancelación asistida."
                )
            )
        if (
            order.state == "on_the_way"
            and not self.env.user.has_group(
                "restaurant_casa_vieja_base.group_restaurant_administrador"
            )
        ):
            raise UserError(_("Solo un administrador puede cancelar pedidos en camino."))

        order.write({"cancel_reason": reason})
        order._action_cancel_direct()
        order.message_post(body=_("Pedido cancelado. Motivo: %s") % reason)

        if self.notify_customer and order.partner_id and order.partner_id.email:
            order.message_post(
                body=_("Su pedido fue cancelado. Motivo: %s") % reason,
                partner_ids=[order.partner_id.id],
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                email_from=self.env.company.email or self.env.user.email_formatted,
            )

        return {"type": "ir.actions.act_window_close"}
