from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    driver_rating_ids = fields.One2many(
        comodel_name="restaurant.delivery.driver.rating",
        inverse_name="driver_id",
        string="Calificaciones como repartidor",
    )
    driver_rating_avg = fields.Float(
        string="Calificacion promedio como repartidor",
        digits=(3, 2),
        compute="_compute_driver_ratings",
        store=True,
    )
    driver_rating_count = fields.Integer(
        string="N° entregas calificadas",
        compute="_compute_driver_ratings",
        store=True,
    )
    driver_polite_pct = fields.Float(
        string="% Amable",
        compute="_compute_driver_ratings",
        store=True,
    )
    driver_on_time_pct = fields.Float(
        string="% Puntual",
        compute="_compute_driver_ratings",
        store=True,
    )
    driver_good_condition_pct = fields.Float(
        string="% Buen estado",
        compute="_compute_driver_ratings",
        store=True,
    )

    @api.depends(
        "driver_rating_ids.rating",
        "driver_rating_ids.was_polite",
        "driver_rating_ids.was_on_time",
        "driver_rating_ids.order_in_good_condition",
    )
    def _compute_driver_ratings(self):
        for user in self:
            ratings = user.driver_rating_ids
            count = len(ratings)
            user.driver_rating_count = count
            if not count:
                user.driver_rating_avg = 0.0
                user.driver_polite_pct = 0.0
                user.driver_on_time_pct = 0.0
                user.driver_good_condition_pct = 0.0
                continue

            user.driver_rating_avg = sum(ratings.mapped("rating")) / count
            user.driver_polite_pct = (
                len(ratings.filtered("was_polite")) * 100.0 / count
            )
            user.driver_on_time_pct = (
                len(ratings.filtered("was_on_time")) * 100.0 / count
            )
            user.driver_good_condition_pct = (
                len(ratings.filtered("order_in_good_condition")) * 100.0 / count
            )

