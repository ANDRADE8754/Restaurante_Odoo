from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DeliveryClaim(models.Model):
    _name = "restaurant.delivery.claim"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Reclamo de pedido delivery"
    _order = "claim_date desc"
    _sql_constraints = [
        (
            "unique_claim_type_per_order",
            "unique(delivery_order_id, claim_type)",
            "Ya existe un reclamo de este tipo para este pedido.",
        ),
    ]

    name = fields.Char(
        string="Referencia",
        required=True,
        readonly=True,
        copy=False,
        default="Nuevo",
    )
    delivery_order_id = fields.Many2one(
        comodel_name="restaurant.delivery.order",
        string="Pedido delivery",
        required=True,
        ondelete="restrict",
        index=True,
        domain=[("state", "=", "delivered")],
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        related="delivery_order_id.partner_id",
        store=True,
    )
    claim_date = fields.Datetime(
        string="Fecha del reclamo",
        default=fields.Datetime.now,
        readonly=True,
    )
    claim_type = fields.Selection(
        selection=[
            ("wrong_item", "Plato equivocado"),
            ("missing_item", "Plato faltante"),
            ("cold_food", "Comida fria"),
            ("damaged", "Pedido dañado"),
            ("late_delivery", "Entrega tardia"),
            ("wrong_quantity", "Cantidad incorrecta"),
            ("other", "Otro"),
        ],
        string="Tipo de reclamo",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Descripcion del problema",
        required=True,
        tracking=True,
    )
    affected_line_ids = fields.Many2many(
        comodel_name="restaurant.delivery.order.line",
        relation="delivery_claim_order_line_rel",
        column1="claim_id",
        column2="line_id",
        string="Productos afectados",
        domain="[('order_id', '=', delivery_order_id)]",
    )
    evidence_note = fields.Text(string="Evidencia/observaciones internas")
    state = fields.Selection(
        selection=[
            ("open", "Abierto"),
            ("in_review", "En revision"),
            ("resolved", "Resuelto"),
            ("rejected", "Rechazado"),
        ],
        string="Estado",
        default="open",
        tracking=True,
        required=True,
    )
    resolution_type = fields.Selection(
        selection=[
            ("resend", "Reenvio"),
            ("credit_note", "Nota de credito"),
            ("discount", "Descuento proximo pedido"),
            ("refund", "Reembolso completo"),
            ("apology", "Disculpa sin compensacion"),
            ("rejected", "Rechazado"),
        ],
        string="Tipo de resolucion",
        tracking=True,
    )
    resolution_notes = fields.Text(string="Detalle de resolucion", tracking=True)
    resolved_by = fields.Many2one(
        comodel_name="res.users",
        string="Resuelto por",
        readonly=True,
    )
    resolved_date = fields.Datetime(string="Fecha de resolucion", readonly=True)
    credit_note_id = fields.Many2one(
        comodel_name="account.move",
        string="Nota de credito vinculada",
        readonly=True,
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Asignado a",
        default=lambda self: self.env.uid,
        tracking=True,
    )

    @api.model
    def _get_claim_hours_limit(self):
        raw_value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.delivery_claim_hours_limit", "48")
        )
        try:
            limit = int(raw_value)
        except (TypeError, ValueError):
            limit = 48
        return max(1, limit)

    @api.model
    def _get_delivery_datetime(self, order):
        delivered_logs = order.state_log_ids.filtered(lambda log: log.state_to == "delivered")
        delivered_logs = delivered_logs.sorted(
            key=lambda log: (log.change_datetime or fields.Datetime.now(), log.id)
        )
        if delivered_logs:
            return delivered_logs[-1].change_datetime
        return order.order_datetime or order.write_date or fields.Datetime.now()

    @api.model
    def _is_order_within_claim_limit(self, order):
        delivery_dt = self._get_delivery_datetime(order)
        limit_hours = self._get_claim_hours_limit()
        return fields.Datetime.now() <= (delivery_dt + timedelta(hours=limit_hours))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "restaurant.delivery.claim"
                ) or "Nuevo"

            order = self.env["restaurant.delivery.order"].browse(vals.get("delivery_order_id"))
            if not order.exists() or order.state != "delivered":
                raise UserError(_("Solo se pueden registrar reclamos para pedidos entregados."))
            if not self._is_order_within_claim_limit(order):
                raise UserError(_("El plazo para reclamos ha expirado."))
        return super().create(vals_list)

    @api.constrains("affected_line_ids", "delivery_order_id")
    def _check_affected_lines_belong_to_order(self):
        for claim in self:
            invalid_lines = claim.affected_line_ids.filtered(
                lambda line: line.order_id != claim.delivery_order_id
            )
            if invalid_lines:
                raise ValidationError(
                    _("Los productos afectados deben pertenecer al pedido seleccionado.")
                )

    def action_review(self):
        for claim in self:
            if claim.state in ("resolved", "rejected"):
                raise UserError(_("No se puede pasar a revision un reclamo cerrado."))
        self.write({"state": "in_review"})

    def _create_credit_note(self):
        self.ensure_one()
        invoice = self.delivery_order_id.invoice_id
        if not invoice or invoice.move_type != "out_invoice":
            return False

        source_lines = invoice.invoice_line_ids.filtered(lambda line: not line.display_type)
        if self.affected_line_ids:
            affected_products = self.affected_line_ids.mapped("product_id").ids
            source_lines = source_lines.filtered(lambda line: line.product_id.id in affected_products)
        if not source_lines:
            source_lines = invoice.invoice_line_ids.filtered(lambda line: not line.display_type)
        if not source_lines:
            return False

        credit_lines = []
        for line in source_lines:
            credit_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": line.name,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "discount": line.discount,
                        "account_id": line.account_id.id,
                        "tax_ids": [(6, 0, line.tax_ids.ids)],
                    },
                )
            )

        credit_note = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": invoice.partner_id.id,
                "currency_id": invoice.currency_id.id,
                "journal_id": invoice.journal_id.id,
                "invoice_origin": invoice.name,
                "invoice_payment_term_id": invoice.invoice_payment_term_id.id,
                "invoice_line_ids": credit_lines,
            }
        )
        return credit_note

    def action_resolve(self):
        now_dt = fields.Datetime.now()
        for claim in self:
            if claim.state not in ("open", "in_review"):
                raise UserError(_("Solo se pueden resolver reclamos abiertos o en revision."))
            if not claim.resolution_type:
                raise UserError(_("Debe seleccionar un tipo de resolucion."))
            if not (claim.resolution_notes or "").strip():
                raise UserError(_("Debe registrar el detalle de resolucion."))

            vals = {
                "state": "resolved",
                "resolved_by": self.env.uid,
                "resolved_date": now_dt,
            }
            if claim.resolution_type == "credit_note" and claim.delivery_order_id.invoice_id:
                credit_note = claim._create_credit_note()
                if credit_note:
                    vals["credit_note_id"] = credit_note.id
            claim.write(vals)
            claim.delivery_order_id.message_post(
                body=_(
                    "Reclamo %(name)s resuelto: %(resolution)s"
                )
                % {
                    "name": claim.name,
                    "resolution": dict(self._fields["resolution_type"].selection).get(
                        claim.resolution_type, claim.resolution_type
                    ),
                }
            )

    def action_reject(self):
        now_dt = fields.Datetime.now()
        for claim in self:
            if claim.state not in ("open", "in_review"):
                raise UserError(_("Solo se pueden rechazar reclamos abiertos o en revision."))
            if not (claim.resolution_notes or "").strip():
                raise UserError(_("Debe indicar una justificacion para rechazar el reclamo."))
            claim.write(
                {
                    "state": "rejected",
                    "resolution_type": "rejected",
                    "resolved_by": self.env.uid,
                    "resolved_date": now_dt,
                }
            )

    def action_reopen(self):
        if not self.env.user.has_group("restaurant_casa_vieja_base.group_restaurant_administrador"):
            raise UserError(_("Solo un administrador puede reabrir reclamos."))
        self.write({"state": "open"})
