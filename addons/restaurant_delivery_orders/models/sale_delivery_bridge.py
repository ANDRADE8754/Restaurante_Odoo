from odoo import fields, models


class DeliveryOrder(models.Model):
    _inherit = "restaurant.delivery.order"

    sale_order_ref = fields.Char(
        string="Referencia de venta web",
        help="Referencia funcional al pedido de tienda nativa (sale.order.name).",
        copy=False,
        index=True,
    )

    source_channel = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("website_sale", "Tienda web"),
        ],
        string="Canal de origen",
        default="manual",
        required=True,
        help="Permite diferenciar pedidos creados desde operación interna vs tienda web.",
    )

    def _prepare_delivery_vals_from_sale_stub(self, sale_order):
        """Fase 1:
        Definición de mapeo sin activar sincronización automática todavía.
        En Fase 3 este método se usará desde la integración con sale.order.
        """
        partner = sale_order.partner_id
        address = (
            sale_order.website_delivery_address
            or self._get_partner_delivery_address(sale_order.partner_shipping_id or partner)
        )
        return {
            "partner_id": partner.id,
            "phone": partner.phone or partner.mobile,
            "email": partner.email,
            "delivery_address": address,
            "delivery_zone_id": sale_order.website_delivery_zone_id.id,
            "delivery_fee": (
                sale_order.website_delivery_zone_id.delivery_fee
                if sale_order.website_delivery_zone_id
                else sale_order._get_default_delivery_fee()
            ),
            "order_datetime": fields.Datetime.now(),
            "payment_method": sale_order.website_payment_method or "cash",
            "notes": sale_order.website_delivery_note,
            "state": "confirmed",
            "sale_order_ref": sale_order.name,
            "source_channel": "website_sale",
        }
