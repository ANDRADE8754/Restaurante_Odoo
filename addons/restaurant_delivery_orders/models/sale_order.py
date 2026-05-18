from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido de delivery",
        copy=False,
        index=True,
        readonly=True,
    )
    website_delivery_address = fields.Text(
        string="Direccion de entrega (web)",
        help="Direccion de entrega capturada en el checkout de la tienda web.",
    )
    website_payment_method = fields.Selection(
        selection=[
            ("cash", "Efectivo"),
            ("transfer", "Transferencia"),
        ],
        string="Metodo de pago (web)",
        default="cash",
        help="Metodo de pago elegido por el cliente en checkout web.",
    )
    website_delivery_note = fields.Text(
        string="Nota de entrega (web)",
        help="Observacion de entrega indicada por el cliente en checkout web.",
    )
    website_delivery_zone_id = fields.Many2one(
        comodel_name="restaurant.delivery.zone",
        string="Zona de entrega web",
        domain=[("active", "=", True)],
    )

    @api.model
    def _get_default_delivery_fee(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.default_delivery_fee", "1.50")
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1.50

    def set_delivery_line(self, carrier, amount):
        """Integracion tienda nativa:
        En pedidos web, usa tarifa fija global configurable.
        """
        for order in self:
            if order.website_id:
                amount = order._get_default_delivery_fee()
                break
        return super().set_delivery_line(carrier, amount)

    def _ensure_website_delivery_method(self):
        """Asegura que el carrito web tenga metodo y costo de entrega visibles."""
        for order in self.filtered("website_id"):
            if not order._has_deliverable_products():
                continue

            delivery_methods = order._get_delivery_methods()
            if not delivery_methods:
                continue

            delivery_method = order._get_preferred_delivery_method(delivery_methods)
            if not delivery_method:
                continue

            rate = {"success": True, "price": order._get_default_delivery_fee()}
            has_delivery_line = bool(order.order_line.filtered("is_delivery"))

            if order.carrier_id != delivery_method or not has_delivery_line:
                order._set_delivery_method(delivery_method, rate=rate)
            else:
                order.set_delivery_line(delivery_method, rate["price"])

    def _cart_update(self, *args, **kwargs):
        result = super()._cart_update(*args, **kwargs)
        self._ensure_website_delivery_method()
        return result

    def _get_website_products_subtotal(self):
        """Subtotal de productos para carrito web, excluyendo envio."""
        self.ensure_one()
        product_lines = self.order_line.filtered(lambda line: not line.is_delivery)
        if self.website_id.show_line_subtotals_tax_selection == "tax_excluded":
            return sum(product_lines.mapped("price_subtotal"))
        return sum(product_lines.mapped("price_total"))

    def _is_website_order_for_delivery(self):
        self.ensure_one()
        return bool(self.website_id)

    def _get_delivery_line_commands_from_sale(self):
        self.ensure_one()
        commands = []
        for line in self.order_line:
            if line.display_type:
                continue
            if not line.product_id:
                continue
            if getattr(line, "is_delivery", False):
                continue
            if line.product_uom_qty <= 0:
                continue
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            commands.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": line.name or line.product_id.display_name,
                        "quantity": line.product_uom_qty,
                        "price_unit": price_unit,
                        "tax_ids": [(6, 0, line.tax_id.ids)],
                    },
                )
            )
        return commands

    def _create_or_link_delivery_order(self):
        self.ensure_one()
        DeliveryOrder = self.env["restaurant.delivery.order"]

        existing = self.delivery_order_id
        if not existing and self.name:
            existing = DeliveryOrder.search([("sale_order_ref", "=", self.name)], limit=1)
        if existing:
            update_vals = {}
            if not existing.sale_order_id:
                update_vals["sale_order_id"] = self.id
            if self.website_delivery_note and not existing.notes:
                update_vals["notes"] = self.website_delivery_note
            update_vals["delivery_fee"] = self._get_default_delivery_fee()
            if update_vals:
                existing.sudo().write(update_vals)
            if self.delivery_order_id != existing:
                self.sudo().write({"delivery_order_id": existing.id})
            return existing

        line_commands = self._get_delivery_line_commands_from_sale()
        if not line_commands:
            return False

        base_vals = DeliveryOrder._prepare_delivery_vals_from_sale_stub(self)
        vals = {
            **base_vals,
            "delivery_fee": self._get_default_delivery_fee(),
            "line_ids": line_commands,
            "sale_order_id": self.id,
        }
        delivery_order = DeliveryOrder.sudo().create(vals)
        self.sudo().write({"delivery_order_id": delivery_order.id})
        return delivery_order

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            if not order._is_website_order_for_delivery():
                continue
            if order.state not in ("sale", "done"):
                continue
            order._create_or_link_delivery_order()
        return result

    def action_cancel(self):
        result = super().action_cancel()
        if self.env.context.get("skip_sale_delivery_sync"):
            return result

        for order in self:
            delivery_order = order.delivery_order_id
            if not delivery_order:
                continue
            if delivery_order.state in ("delivered", "cancelled"):
                continue
            delivery_order.with_context(skip_delivery_sale_sync=True).write(
                {"state": "cancelled"}
            )
        return result
