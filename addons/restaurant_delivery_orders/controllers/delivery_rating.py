from odoo import http
from odoo.http import request


class DeliveryRatingController(http.Controller):
    def _get_portal_sale_order(self, order_id):
        sale_order = request.env["sale.order"].sudo().browse(order_id)
        if not sale_order.exists():
            return request.env["sale.order"]

        user_partner = request.env.user.partner_id.commercial_partner_id
        order_partner = sale_order.partner_id.commercial_partner_id
        if user_partner != order_partner:
            return request.env["sale.order"]
        return sale_order

    @http.route(
        ["/my/orders/<int:order_id>/rate"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_delivery_rate_get(self, order_id, **kwargs):
        sale_order = self._get_portal_sale_order(order_id)
        if not sale_order:
            return request.redirect("/my/orders")

        delivery_order = sale_order.delivery_order_id
        if not delivery_order or delivery_order.state != "delivered":
            return request.redirect(f"/my/orders/{sale_order.id}")

        return request.render(
            "restaurant_delivery_orders.portal_delivery_order_rating",
            {
                "sale_order": sale_order,
                "delivery_order": delivery_order,
                "page_name": "delivery_rating",
            },
        )

    @http.route(
        ["/my/orders/<int:order_id>/rate"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_delivery_rate_post(self, order_id, **post):
        sale_order = self._get_portal_sale_order(order_id)
        if not sale_order:
            return request.redirect("/my/orders")

        delivery_order = sale_order.delivery_order_id
        if not delivery_order or delivery_order.state != "delivered":
            return request.redirect(f"/my/orders/{sale_order.id}")

        Rating = request.env["restaurant.delivery.product.rating"]
        DriverRating = request.env["restaurant.delivery.driver.rating"]
        for line in delivery_order.line_ids.filtered("product_id"):
            rating_key = f"rating_{line.id}"
            if rating_key not in post:
                continue

            rating_value = post.get(rating_key)
            try:
                rating_int = int(rating_value)
            except (TypeError, ValueError):
                continue
            if rating_int < 1 or rating_int > 5:
                continue

            existing = Rating.sudo().search([("delivery_line_id", "=", line.id)], limit=1)
            if existing:
                continue

            comment = (post.get(f"comment_{line.id}") or "").strip()
            vals = {
                "delivery_order_id": delivery_order.id,
                "delivery_line_id": line.id,
                "rating": rating_int,
                "comment": comment,
            }
            Rating.sudo().create(vals)

        if delivery_order.delivery_user_id:
            existing_driver_rating = DriverRating.sudo().search(
                [("delivery_order_id", "=", delivery_order.id)],
                limit=1,
            )
            if not existing_driver_rating:
                driver_rating_raw = post.get("driver_rating")
                try:
                    driver_rating_int = int(driver_rating_raw)
                except (TypeError, ValueError):
                    driver_rating_int = 0

                if 1 <= driver_rating_int <= 5:
                    DriverRating.sudo().create(
                        {
                            "delivery_order_id": delivery_order.id,
                            "driver_id": delivery_order.delivery_user_id.id,
                            "rating": driver_rating_int,
                            "comment": (post.get("driver_comment") or "").strip(),
                            "was_polite": bool(post.get("was_polite")),
                            "was_on_time": bool(post.get("was_on_time")),
                            "order_in_good_condition": bool(
                                post.get("order_in_good_condition")
                            ),
                        }
                    )

        return request.redirect(f"/my/orders/{sale_order.id}?delivery_rating_thanks=1")
