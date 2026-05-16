from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    delivery_rating_ids = fields.One2many(
        comodel_name="restaurant.delivery.product.rating",
        inverse_name="product_id",
        string="Calificaciones delivery",
    )
    delivery_rating_avg = fields.Float(
        string="Calificacion delivery promedio",
        digits=(3, 2),
        compute="_compute_delivery_rating",
        store=True,
    )
    delivery_rating_count = fields.Integer(
        string="N° calificaciones",
        compute="_compute_delivery_rating",
        store=True,
    )

    @api.depends("delivery_rating_ids.rating")
    def _compute_delivery_rating(self):
        for product in self:
            ratings = product.delivery_rating_ids.mapped("rating")
            product.delivery_rating_count = len(ratings)
            product.delivery_rating_avg = (
                sum(ratings) / len(ratings) if ratings else 0.0
            )

