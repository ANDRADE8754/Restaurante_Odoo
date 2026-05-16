from odoo import api, fields, models


class DeliveryStateLog(models.Model):
    _name = "restaurant.delivery.state.log"
    _description = "Historial de estados de pedido delivery"
    _order = "change_datetime asc"

    @api.model
    def _state_selection(self):
        return self.env["restaurant.delivery.order"]._fields["state"].selection

    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido",
        required=True,
        ondelete="cascade",
        index=True,
    )
    state_from = fields.Selection(
        selection=_state_selection,
        string="Estado anterior",
    )
    state_to = fields.Selection(
        selection=_state_selection,
        string="Estado nuevo",
        required=True,
    )
    change_datetime = fields.Datetime(
        string="Fecha de cambio",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Realizado por",
        required=True,
        default=lambda self: self.env.uid,
    )
    duration_in_state = fields.Float(
        string="Minutos en estado anterior",
        compute="_compute_duration_in_state",
        store=True,
    )

    @api.depends(
        "change_datetime",
        "delivery_order_id",
        "delivery_order_id.state_log_ids.change_datetime",
        "delivery_order_id.state_log_ids.create_date",
    )
    def _compute_duration_in_state(self):
        for log in self:
            log.duration_in_state = 0.0
            if not log.delivery_order_id or not log.change_datetime:
                continue

            previous_log = self.search(
                [
                    ("delivery_order_id", "=", log.delivery_order_id.id),
                    ("id", "!=", log.id),
                    "|",
                    ("change_datetime", "<", log.change_datetime),
                    "&",
                    ("change_datetime", "=", log.change_datetime),
                    ("id", "<", log.id),
                ],
                order="change_datetime desc, id desc",
                limit=1,
            )
            if not previous_log or not previous_log.change_datetime:
                continue

            delta = log.change_datetime - previous_log.change_datetime
            log.duration_in_state = max(delta.total_seconds() / 60.0, 0.0)
