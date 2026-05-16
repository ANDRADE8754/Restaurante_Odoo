from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeliveryDriverRating(models.Model):
    _name = "restaurant.delivery.driver.rating"
    _description = "Calificacion de repartidor"
    _order = "rating_date desc"
    _sql_constraints = [
        (
            "unique_order_driver_rating",
            "unique(delivery_order_id)",
            "Solo se puede calificar al repartidor una vez por pedido.",
        ),
    ]

    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido delivery",
        required=True,
        ondelete="cascade",
        index=True,
    )
    driver_id = fields.Many2one(
        comodel_name="res.users",
        string="Repartidor",
        required=True,
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        related="delivery_order_id.partner_id",
        store=True,
        required=True,
    )
    rating = fields.Integer(
        string="Calificacion",
        required=True,
    )
    comment = fields.Text(string="Comentario sobre la entrega")
    rating_date = fields.Datetime(
        string="Fecha de calificacion",
        default=fields.Datetime.now,
        readonly=True,
    )
    was_polite = fields.Boolean(string="Amable", default=False)
    was_on_time = fields.Boolean(string="Puntual", default=False)
    order_in_good_condition = fields.Boolean(
        string="Pedido en buen estado",
        default=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order_id = vals.get("delivery_order_id")
            if vals.get("driver_id") or not order_id:
                continue
            order = self.env["restaurant.delivery.order"].browse(order_id)
            if order.exists() and order.delivery_user_id:
                vals["driver_id"] = order.delivery_user_id.id
        return super().create(vals_list)

    @api.constrains("rating")
    def _check_rating_range(self):
        for record in self:
            if record.rating < 1 or record.rating > 5:
                raise ValidationError("La calificacion debe estar entre 1 y 5 estrellas.")

    @api.constrains("delivery_order_id", "driver_id")
    def _check_driver_consistency(self):
        for record in self:
            order = record.delivery_order_id
            if not order:
                continue
            if order.state != "delivered":
                raise ValidationError("Solo se puede calificar al repartidor en pedidos entregados.")
            if not order.delivery_user_id:
                raise ValidationError("No se puede calificar un pedido sin repartidor asignado.")
            if record.driver_id != order.delivery_user_id:
                raise ValidationError(
                    "El repartidor calificado no coincide con el repartidor del pedido."
                )

