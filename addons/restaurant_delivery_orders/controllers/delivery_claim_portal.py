from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError


class DeliveryClaimPortalController(http.Controller):
    def _get_portal_sale_order(self, order_id):
        sale_order = request.env["sale.order"].sudo().browse(order_id)
        if not sale_order.exists():
            return request.env["sale.order"]

        user_partner = request.env.user.partner_id.commercial_partner_id
        order_partner = sale_order.partner_id.commercial_partner_id
        if user_partner != order_partner:
            return request.env["sale.order"]
        return sale_order

    def _can_open_claim(self, delivery_order):
        if not delivery_order or delivery_order.state != "delivered":
            return False
        if not delivery_order._is_within_claim_window():
            return False
        has_open_claim = bool(
            delivery_order.claim_ids.filtered(lambda claim: claim.state in ("open", "in_review"))
        )
        return not has_open_claim

    @http.route(
        ["/my/orders/<int:order_id>/claim"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_delivery_claim_get(self, order_id, **kwargs):
        sale_order = self._get_portal_sale_order(order_id)
        if not sale_order:
            return request.redirect("/my/orders")

        delivery_order = sale_order.delivery_order_id
        if not delivery_order or delivery_order.state != "delivered":
            return request.redirect(f"/my/orders/{sale_order.id}")
        if not self._can_open_claim(delivery_order):
            return request.redirect(f"/my/orders/{sale_order.id}?claim_unavailable=1")

        return request.render(
            "restaurant_delivery_orders.portal_delivery_claim_form",
            {
                "sale_order": sale_order,
                "delivery_order": delivery_order,
                "page_name": "delivery_claim",
            },
        )

    @http.route(
        ["/my/orders/<int:order_id>/claim"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_delivery_claim_post(self, order_id, **post):
        sale_order = self._get_portal_sale_order(order_id)
        if not sale_order:
            return request.redirect("/my/orders")

        delivery_order = sale_order.delivery_order_id
        if not delivery_order or delivery_order.state != "delivered":
            return request.redirect(f"/my/orders/{sale_order.id}")
        if not self._can_open_claim(delivery_order):
            return request.redirect(f"/my/orders/{sale_order.id}?claim_unavailable=1")

        claim_type = (post.get("claim_type") or "").strip()
        description = (post.get("description") or "").strip()
        if not claim_type or not description:
            return request.redirect(
                f"/my/orders/{sale_order.id}/claim?claim_error=required"
            )
        valid_claim_types = dict(
            request.env["restaurant.delivery.claim"]._fields["claim_type"].selection
        )
        if claim_type not in valid_claim_types:
            return request.redirect(
                f"/my/orders/{sale_order.id}/claim?claim_error=required"
            )

        line_ids_raw = request.httprequest.form.getlist("affected_line_ids")
        line_ids = []
        for line_id in line_ids_raw:
            try:
                line_ids.append(int(line_id))
            except (TypeError, ValueError):
                continue
        valid_lines = delivery_order.line_ids.filtered(lambda line: line.id in line_ids)

        vals = {
            "delivery_order_id": delivery_order.id,
            "claim_type": claim_type,
            "description": description,
            "affected_line_ids": [(6, 0, valid_lines.ids)],
        }
        try:
            request.env["restaurant.delivery.claim"].sudo().create(vals)
        except (UserError, ValidationError):
            return request.redirect(
                f"/my/orders/{sale_order.id}/claim?claim_error=duplicate"
            )

        return request.redirect(f"/my/orders/{sale_order.id}?claim_created=1")

    @http.route(
        ["/my/claims"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_my_claims(self, **kwargs):
        user_partner = request.env.user.partner_id.commercial_partner_id
        claims = (
            request.env["restaurant.delivery.claim"]
            .sudo()
            .search([("partner_id", "child_of", user_partner.id)], order="claim_date desc")
        )
        return request.render(
            "restaurant_delivery_orders.portal_my_claims",
            {
                "claims": claims,
                "page_name": "my_claims",
            },
        )

    @http.route(
        ["/my/claims/<int:claim_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_claim_detail(self, claim_id, **kwargs):
        claim = request.env["restaurant.delivery.claim"].sudo().browse(claim_id)
        if not claim.exists():
            return request.redirect("/my/claims")

        user_partner = request.env.user.partner_id.commercial_partner_id
        if claim.partner_id.commercial_partner_id != user_partner:
            return request.redirect("/my/claims")

        return request.render(
            "restaurant_delivery_orders.portal_claim_detail",
            {
                "claim": claim,
                "page_name": "my_claims",
            },
        )
