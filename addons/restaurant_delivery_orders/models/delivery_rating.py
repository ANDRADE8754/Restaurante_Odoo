from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeliveryProductRating(models.Model):
    _name = "restaurant.delivery.product.rating"
    _description = "Calificacion de producto en pedido delivery"
    _order = "rating_date desc"
    _sql_constraints = [
        (
            "unique_line_rating",
            "unique(delivery_line_id)",
            "Solo se puede calificar cada plato una vez por pedido.",
        ),
    ]

    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido delivery",
        required=True,
        ondelete="cascade",
        index=True,
    )
    delivery_line_id = fields.Many2one(
        comodel_name="restaurant.delivery.order.line",
        string="Linea del pedido",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto",
        related="delivery_line_id.product_id",
        store=True,
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
    comment = fields.Text(string="Comentario")
    rating_date = fields.Datetime(
        string="Fecha de calificacion",
        default=fields.Datetime.now,
        readonly=True,
    )

    @api.constrains("rating")
    def _check_rating_range(self):
        for record in self:
            if record.rating < 1 or record.rating > 5:
                raise ValidationError("La calificacion debe estar entre 1 y 5 estrellas.")

    @api.constrains("delivery_order_id", "delivery_line_id")
    def _check_order_line_consistency(self):
        for record in self:
            if (
                record.delivery_order_id
                and record.delivery_line_id
                and record.delivery_line_id.order_id != record.delivery_order_id
            ):
                raise ValidationError(
                    "La linea calificada no pertenece al pedido seleccionado."
                )
