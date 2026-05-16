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
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Impuestos aplicados",
        domain=[("type_tax_use", "=", "sale")],
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amounts",
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        string="Impuestos",
        compute="_compute_amounts",
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="order_id.currency_id",
        store=True,
        readonly=True,
    )
    kitchen_note = fields.Text(string="Nota para cocina")
    rating_id = fields.One2many(
        comodel_name="restaurant.delivery.product.rating",
        inverse_name="delivery_line_id",
        string="Calificacion",
    )
    is_rated = fields.Boolean(
        string="Calificado",
        compute="_compute_is_rated",
    )

    @api.depends("quantity", "price_unit", "tax_ids", "currency_id")
    def _compute_amounts(self):
        for line in self:
            taxes_res = line.tax_ids.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )
            line.price_subtotal = taxes_res["total_excluded"]
            line.price_total = taxes_res["total_included"]
            line.price_tax = line.price_total - line.price_subtotal

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.price_unit = self.product_id.lst_price
            order_company = (
                self.order_id.company_id
                if self.order_id and "company_id" in self.order_id._fields
                else self.env.company
            )
            self.tax_ids = self.product_id.taxes_id.filtered(
                lambda t: t.company_id == order_company
            )

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("La cantidad debe ser mayor que cero.")

    @api.depends("rating_id")
    def _compute_is_rated(self):
        for line in self:
            line.is_rated = bool(line.rating_id)
