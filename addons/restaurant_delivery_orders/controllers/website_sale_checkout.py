from odoo.http import route
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleCheckoutDeliveryFields(WebsiteSale):
    def _get_delivery_schedule_status(self):
        return request.env["restaurant.delivery.schedule"].sudo().is_delivery_available()

    def _checkout_login_redirect(self, target="/shop/checkout"):
        return request.redirect(f"/web/login?redirect={target}")

    def _ensure_registered_user_for_purchase(self, target="/shop/checkout"):
        if request.env.user._is_public():
            return self._checkout_login_redirect(target)
        return None

    @route(
        ["/shop/cart"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def cart(self, access_token=None, revive="", **post):
        if redirection := self._ensure_registered_user_for_purchase("/shop/cart"):
            return redirection
        order = request.website.sale_get_order()
        if order:
            order._ensure_website_delivery_method()
        return super().cart(access_token=access_token, revive=revive, **post)

    @route(
        ["/shop/cart/update"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_update(
        self,
        product_id,
        add_qty=1,
        set_qty=0,
        product_custom_attribute_values=None,
        no_variant_attribute_value_ids=None,
        **kwargs,
    ):
        if redirection := self._ensure_registered_user_for_purchase("/shop/cart"):
            return redirection
        return super().cart_update(
            product_id=product_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs,
        )

    @route(
        ["/shop/cart/update_json"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_update_json(
        self,
        product_id,
        line_id=None,
        add_qty=None,
        set_qty=None,
        display=True,
        product_custom_attribute_values=None,
        no_variant_attribute_value_ids=None,
        **kwargs,
    ):
        if request.env.user._is_public():
            return {
                "warning": "Debes iniciar sesión para comprar.",
                "redirect_url": "/web/login?redirect=/shop/cart",
            }
        return super().cart_update_json(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            display=display,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs,
        )

    @route(
        "/shop/checkout",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def shop_checkout(self, try_skip_step=None, **query_params):
        if redirection := self._ensure_registered_user_for_purchase("/shop/checkout"):
            return redirection
        order = request.website.sale_get_order()
        if order:
            order._ensure_website_delivery_method()
        response = super().shop_checkout(try_skip_step=try_skip_step, **query_params)
        if hasattr(response, "qcontext"):
            is_available, message = self._get_delivery_schedule_status()
            response.qcontext.update(
                {
                    "delivery_closed": not is_available,
                    "delivery_closed_message": message,
                }
            )
        return response

    @route(
        ["/shop/address"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def address(self, *args, **kwargs):
        if redirection := self._ensure_registered_user_for_purchase("/shop/checkout"):
            return redirection
        response = super().address(*args, **kwargs)
        if hasattr(response, "qcontext"):
            is_available, message = self._get_delivery_schedule_status()
            response.qcontext.update(
                {
                    "delivery_closed": not is_available,
                    "delivery_closed_message": message,
                }
            )
        return response

    @route(
        ["/shop/confirm_order"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def confirm_order(self, **post):
        if redirection := self._ensure_registered_user_for_purchase("/shop/checkout"):
            return redirection
        is_available, _message = self._get_delivery_schedule_status()
        if not is_available:
            return request.redirect("/shop/checkout")
        return super().confirm_order(**post)

    def _check_addresses(self, order_sudo):
        # Keep native checks and force registered users to complete address fields.
        if redirection := super()._check_addresses(order_sudo):
            return redirection

        if request.env.user._is_public():
            return self._checkout_login_redirect("/shop/checkout")

        partner = order_sudo.partner_shipping_id or order_sudo.partner_id
        if not self._check_delivery_address(partner):
            return request.redirect("/shop/address?address_type=delivery")

    def _handle_extra_form_data(self, extra_form_data, address_values):
        super()._handle_extra_form_data(extra_form_data, address_values)

        order = request.website.sale_get_order()
        if not order:
            return

        vals = {}

        delivery_address = (extra_form_data.get("cv_delivery_address") or "").strip()
        if delivery_address:
            vals["website_delivery_address"] = delivery_address

        delivery_note = (extra_form_data.get("cv_delivery_note") or "").strip()
        if delivery_note:
            vals["website_delivery_note"] = delivery_note

        payment_method = extra_form_data.get("cv_payment_method")
        if payment_method in ("cash", "transfer"):
            vals["website_payment_method"] = payment_method

        zone_id = extra_form_data.get("cv_delivery_zone_id")
        zone_id_int = False
        if zone_id:
            try:
                zone_id_int = int(zone_id)
            except (TypeError, ValueError):
                zone_id_int = False
        if zone_id_int:
            zone = (
                request.env["restaurant.delivery.zone"]
                .sudo()
                .search([("id", "=", zone_id_int), ("active", "=", True)], limit=1)
            )
            vals["website_delivery_zone_id"] = zone.id or False
        elif "cv_delivery_zone_id" in extra_form_data:
            vals["website_delivery_zone_id"] = False

        if vals:
            order.sudo().write(vals)
