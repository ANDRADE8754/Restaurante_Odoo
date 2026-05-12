from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DeliveryOrder(models.Model):
    _name = "restaurant.delivery.order"
    _description = "Pedido a Domicilio"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "order_datetime desc, name desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        required=True,
        tracking=True,
    )
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Correo electrónico")
    delivery_address = fields.Text(string="Dirección de entrega", required=True)
    order_datetime = fields.Datetime(
        string="Fecha del pedido",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    estimated_delivery_datetime = fields.Datetime(string="Entrega estimada")
    delivery_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Repartidor asignado",
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsable",
        default=lambda self: self.env.user,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("confirmed", "Confirmado"),
            ("preparing", "En preparación"),
            ("on_the_way", "En camino"),
            ("delivered", "Entregado"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="restaurant.delivery.order.line",
        inverse_name="order_id",
        string="Líneas del pedido",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    amount_untaxed = fields.Monetary(
        string="Subtotal",
        compute="_compute_amounts",
        currency_field="currency_id",
    )
    delivery_fee = fields.Monetary(
        string="Costo de entrega",
        currency_field="currency_id",
        default=1.50,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        currency_field="currency_id",
    )
    payment_method = fields.Selection(
        selection=[
            ("cash", "Efectivo"),
            ("card", "Tarjeta"),
            ("transfer", "Transferencia"),
        ],
        string="Método de pago",
    )
    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pedido POS relacionado",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Factura relacionada",
    )
    notes = fields.Text(string="Observaciones")
    kitchen_notes = fields.Text(string="Observaciones para cocina")

    @api.depends("line_ids.price_subtotal", "delivery_fee")
    def _compute_amounts(self):
        for order in self:
            order.amount_untaxed = sum(order.line_ids.mapped("price_subtotal"))
            order.amount_total = order.amount_untaxed + order.delivery_fee

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "restaurant.delivery.order"
                ) or "Nuevo"
        return super().create(vals_list)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.phone or self.partner_id.mobile
            self.email = self.partner_id.email
            self.delivery_address = self._get_partner_delivery_address(self.partner_id)

    def _get_partner_delivery_address(self, partner):
        return "\n".join(
            filter(
                None,
                [
                    partner.street,
                    partner.street2,
                    " ".join(filter(None, [partner.city, partner.state_id.name])),
                    partner.country_id.name,
                ],
            )
        )

    @api.constrains("order_datetime", "estimated_delivery_datetime")
    def _check_estimated_delivery_datetime(self):
        for order in self:
            if (
                order.estimated_delivery_datetime
                and order.order_datetime
                and order.estimated_delivery_datetime < order.order_datetime
            ):
                raise ValidationError(
                    _("La entrega estimada debe ser mayor o igual a la fecha del pedido.")
                )

    def _validate_required_for_confirmation(self):
        for order in self:
            if not order.delivery_address:
                raise UserError(_("No se puede confirmar un pedido sin dirección de entrega."))
            if not order.line_ids:
                raise UserError(_("No se puede confirmar un pedido sin líneas."))

    def action_confirm(self):
        self._validate_required_for_confirmation()
        self.write({"state": "confirmed"})

    def action_prepare(self):
        self.write({"state": "preparing"})

    def action_send(self):
        self.write({"state": "on_the_way"})

    def action_deliver(self):
        for order in self:
            if order.state != "on_the_way":
                raise UserError(
                    _("Solo se puede entregar un pedido que esté en camino.")
                )
        self.write({"state": "delivered"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
