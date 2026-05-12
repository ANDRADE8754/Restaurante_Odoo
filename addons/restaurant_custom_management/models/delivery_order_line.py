from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeliveryOrderLine(models.Model):
    _name = "restaurant.delivery.order.line"
    _description = "Línea de Pedido a Domicilio"

    order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto",
        required=True,
        domain=[("sale_ok", "=", True)],
    )
    name = fields.Text(string="Descripción")
    quantity = fields.Float(string="Cantidad", default=1.0, required=True)
    price_unit = fields.Monetary(
        string="Precio unitario",
        currency_field="currency_id",
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_price_subtotal",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="order_id.currency_id",
        store=True,
        readonly=True,
    )
    kitchen_note = fields.Text(string="Nota para cocina")

    @api.depends("quantity", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.price_unit = self.product_id.lst_price

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("La cantidad debe ser mayor que cero.")
