from odoo import http
from odoo.http import request


class CasaViejaLegacyRoutes(http.Controller):
    """Fase 7:
    Retiro de flujo custom /casavieja/* en favor de website_sale nativo.
    Se mantienen rutas legacy solo como puente de compatibilidad.
    """

    @http.route("/casavieja/menu", type="http", auth="user", methods=["GET"], website=True)
    def legacy_menu(self, **kwargs):
        return request.redirect("/shop")

    @http.route(
        "/casavieja/carrito/agregar",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def legacy_add_to_cart(self, product_id=None, quantity=1, **kwargs):
        try:
            pid = int(product_id or 0)
            qty = float(quantity or 1)
        except (TypeError, ValueError):
            return request.redirect("/shop")

        if pid <= 0 or qty <= 0:
            return request.redirect("/shop")

        order = request.website.sale_get_order(force_create=True)
        order._cart_update(product_id=pid, add_qty=qty)
        return request.redirect("/shop/cart")

    @http.route("/casavieja/carrito", type="http", auth="user", methods=["GET"], website=True)
    def legacy_cart(self, **kwargs):
        return request.redirect("/shop/cart")

    @http.route("/casavieja/checkout", type="http", auth="user", methods=["POST"], website=True)
    def legacy_checkout(self, **kwargs):
        return request.redirect("/shop/checkout")

    @http.route("/casavieja/mis-pedidos", type="http", auth="user", methods=["GET"], website=True)
    def legacy_my_orders(self, **kwargs):
        return request.redirect("/my/orders")

    @http.route(
        "/casavieja/mis-pedidos/<int:order_id>",
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def legacy_my_order_detail(self, order_id, **kwargs):
        return request.redirect("/my/orders")

    @http.route(
        "/casavieja/api/order-status/<int:order_id>",
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def legacy_order_status_api(self, order_id, **kwargs):
        return request.make_json_response({"deprecated": True, "redirect": "/my/orders"})
