from datetime import timedelta
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DeliveryOrder(models.Model):
    _name = "restaurant.delivery.order"
    _description = "Pedido a Domicilio"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "order_datetime desc, name desc"
    ALLOWED_TRANSITIONS = {
        "draft": ["confirmed", "cancelled"],
        "confirmed": ["preparing", "cancelled"],
        "preparing": ["on_the_way", "cancelled"],
        "on_the_way": ["delivered", "cancelled"],
        "delivered": [],
        "cancelled": ["draft"],
    }
    STATE_MAIL_TEMPLATES = {
        "confirmed": "restaurant_delivery_orders.mail_template_delivery_confirmed",
        "preparing": "restaurant_delivery_orders.mail_template_delivery_preparing",
        "on_the_way": "restaurant_delivery_orders.mail_template_delivery_on_the_way",
        "delivered": "restaurant_delivery_orders.mail_template_delivery_delivered",
        "cancelled": "restaurant_delivery_orders.mail_template_delivery_cancelled",
    }
    INVOICE_MAIL_TEMPLATE = "restaurant_delivery_orders.mail_template_delivery_invoice"
    LOCKED_STATES = ("delivered", "cancelled")
    DRIVER_WRITE_ALLOWED_FIELDS = {"state"}
    LOCKED_WRITE_BLOCKED_FIELDS = {
        "partner_id",
        "phone",
        "email",
        "delivery_address",
        "delivery_zone_id",
        "order_datetime",
        "estimated_delivery_datetime",
        "delivery_user_id",
        "responsible_id",
        "line_ids",
        "currency_id",
        "delivery_fee",
        "amount_untaxed",
        "amount_tax",
        "amount_total",
        "payment_method",
        "notes",
        "kitchen_notes",
        "sale_order_id",
        "pos_order_id",
        "source_channel",
        "sale_order_ref",
    }

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
    phone = fields.Char(string="Telefono")
    email = fields.Char(string="Correo electronico")
    delivery_address = fields.Text(string="Direccion de entrega", required=True)
    delivery_zone_id = fields.Many2one(
        comodel_name="restaurant.delivery.zone",
        string="Zona de entrega",
        domain=[("active", "=", True)],
        tracking=True,
    )
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
    delivery_user_active_count = fields.Integer(
        string="Pedidos activos del repartidor",
        compute="_compute_delivery_user_workload",
    )
    delivery_user_is_overloaded = fields.Boolean(
        string="Repartidor sobrecargado",
        compute="_compute_delivery_user_workload",
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
            ("preparing", "En preparacion"),
            ("on_the_way", "En camino"),
            ("delivered", "Entregado"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    state_log_ids = fields.One2many(
        comodel_name="restaurant.delivery.state.log",
        inverse_name="delivery_order_id",
        string="Historial de estados",
    )
    product_rating_ids = fields.One2many(
        comodel_name="restaurant.delivery.product.rating",
        inverse_name="delivery_order_id",
        string="Calificaciones de productos",
    )
    driver_rating_id = fields.One2many(
        comodel_name="restaurant.delivery.driver.rating",
        inverse_name="delivery_order_id",
        string="Calificacion de repartidor",
    )
    claim_ids = fields.One2many(
        comodel_name="restaurant.delivery.claim",
        inverse_name="delivery_order_id",
        string="Reclamos vinculados",
    )
    claim_count = fields.Integer(
        string="Reclamos",
        compute="_compute_claim_metrics",
    )
    open_claim_count = fields.Integer(
        string="Reclamos abiertos",
        compute="_compute_claim_metrics",
    )
    can_create_claim = fields.Boolean(
        string="Puede crear reclamo",
        compute="_compute_claim_metrics",
    )
    is_fully_rated = fields.Boolean(
        string="Todo calificado",
        compute="_compute_is_fully_rated",
        store=True,
    )
    average_rating = fields.Float(
        string="Calificacion promedio",
        digits=(3, 2),
        compute="_compute_average_rating",
    )
    is_driver_rated = fields.Boolean(
        string="Repartidor calificado",
        compute="_compute_driver_rating_metrics",
    )
    driver_rating_value = fields.Integer(
        string="Calificacion del repartidor",
        compute="_compute_driver_rating_metrics",
    )
    delivery_user_rating_avg = fields.Float(
        string="Promedio del repartidor",
        related="delivery_user_id.driver_rating_avg",
        readonly=True,
    )
    minutes_to_prepare = fields.Float(
        string="Minutos a preparacion",
        compute="_compute_delivery_times",
    )
    minutes_to_dispatch = fields.Float(
        string="Minutos a despacho",
        compute="_compute_delivery_times",
    )
    minutes_to_deliver = fields.Float(
        string="Minutos a entrega",
        compute="_compute_delivery_times",
    )
    minutes_total = fields.Float(
        string="Minutos totales",
        compute="_compute_delivery_times",
    )
    line_ids = fields.One2many(
        comodel_name="restaurant.delivery.order.line",
        inverse_name="order_id",
        string="Lineas del pedido",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    amount_untaxed = fields.Monetary(
        string="Subtotal",
        compute="_compute_amount_totals",
        currency_field="currency_id",
    )
    amount_tax = fields.Monetary(
        string="Impuestos",
        compute="_compute_amount_tax",
        store=True,
        currency_field="currency_id",
    )
    delivery_fee = fields.Monetary(
        string="Costo de entrega",
        currency_field="currency_id",
        default=lambda self: float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.default_delivery_fee", "1.50")
        ),
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amount_totals",
        currency_field="currency_id",
    )
    payment_method = fields.Selection(
        selection=[
            ("cash", "Efectivo"),
            ("transfer", "Transferencia"),
        ],
        string="Metodo de pago",
        default="cash",
    )
    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pedido POS relacionado",
    )
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Pedido web relacionado",
        copy=False,
        index=True,
        readonly=True,
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Factura relacionada",
    )
    invoice_state = fields.Selection(
        related="invoice_id.state",
        string="Estado de factura",
    )
    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Estado de pago",
    )
    cancel_reason = fields.Text(
        string="Motivo de cancelacion",
        readonly=True,
        tracking=True,
    )
    notes = fields.Text(string="Observaciones")
    kitchen_notes = fields.Text(string="Observaciones para cocina")

    @api.depends("line_ids.price_subtotal", "line_ids.price_total", "delivery_fee")
    def _compute_amount_totals(self):
        for order in self:
            order.amount_untaxed = sum(order.line_ids.mapped("price_subtotal"))
            order.amount_total = sum(order.line_ids.mapped("price_total")) + order.delivery_fee

    @api.depends("line_ids.price_tax")
    def _compute_amount_tax(self):
        for order in self:
            order.amount_tax = sum(order.line_ids.mapped("price_tax"))

    @api.depends("state_log_ids.change_datetime", "state_log_ids.state_to")
    def _compute_delivery_times(self):
        for order in self:
            order.minutes_to_prepare = 0.0
            order.minutes_to_dispatch = 0.0
            order.minutes_to_deliver = 0.0
            order.minutes_total = 0.0

            state_dates = {}
            ordered_logs = order.state_log_ids.sorted(
                key=lambda log: (log.change_datetime or fields.Datetime.now(), log.id)
            )
            for log in ordered_logs:
                if log.state_to and log.change_datetime and log.state_to not in state_dates:
                    state_dates[log.state_to] = log.change_datetime

            def _duration_minutes(state_start, state_end):
                start = state_dates.get(state_start)
                end = state_dates.get(state_end)
                if not start or not end or end < start:
                    return 0.0
                return (end - start).total_seconds() / 60.0

            order.minutes_to_prepare = _duration_minutes("confirmed", "preparing")
            order.minutes_to_dispatch = _duration_minutes("preparing", "on_the_way")
            order.minutes_to_deliver = _duration_minutes("on_the_way", "delivered")
            order.minutes_total = _duration_minutes("confirmed", "delivered")

    @api.depends("product_rating_ids.rating")
    def _compute_average_rating(self):
        for order in self:
            ratings = order.product_rating_ids.mapped("rating")
            order.average_rating = sum(ratings) / len(ratings) if ratings else 0.0

    @api.depends("line_ids.product_id", "product_rating_ids.delivery_line_id")
    def _compute_is_fully_rated(self):
        for order in self:
            line_ids = order.line_ids.filtered("product_id").ids
            rated_line_ids = order.product_rating_ids.mapped("delivery_line_id").ids
            order.is_fully_rated = bool(line_ids) and all(
                line_id in rated_line_ids for line_id in line_ids
            )

    @api.depends("driver_rating_id.rating")
    def _compute_driver_rating_metrics(self):
        for order in self:
            driver_rating = order.driver_rating_id[:1]
            order.is_driver_rated = bool(driver_rating)
            order.driver_rating_value = driver_rating.rating if driver_rating else 0

    @api.depends("claim_ids.state", "state", "state_log_ids.change_datetime")
    def _compute_claim_metrics(self):
        for order in self:
            order.claim_count = len(order.claim_ids)
            order.open_claim_count = len(
                order.claim_ids.filtered(lambda claim: claim.state in ("open", "in_review"))
            )
            order.can_create_claim = order._is_within_claim_window()

    @api.model
    def _get_max_concurrent_orders(self):
        raw_value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.delivery_max_concurrent_orders", "5")
        )
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return 5

    @api.model
    def _get_int_config_param(self, key, default_value):
        raw_value = self.env["ir.config_parameter"].sudo().get_param(key, str(default_value))
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return default_value

    @api.model
    def _get_claim_hours_limit(self):
        return self._get_int_config_param("restaurant.delivery_claim_hours_limit", 48)

    @api.model
    def _get_default_delivery_fee(self):
        raw_value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.default_delivery_fee", "1.50")
        )
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return 1.50

    @api.model
    def _get_delivery_drivers(self):
        group = self.env.ref(
            "restaurant_casa_vieja_base.group_restaurant_repartidor",
            raise_if_not_found=False,
        )
        if not group:
            return self.env["res.users"]
        return group.users.filtered(lambda user: user.active and not user.share)

    def _select_best_driver(self):
        self.ensure_one()
        drivers = self._get_delivery_drivers()
        if not drivers:
            return self.env["res.users"]

        active_states = ("confirmed", "preparing", "on_the_way")
        order_model = self.env["restaurant.delivery.order"].sudo()
        workloads = []
        for driver in drivers:
            count = order_model.search_count(
                [
                    ("delivery_user_id", "=", driver.id),
                    ("state", "in", active_states),
                    ("id", "!=", self.id),
                ]
            )
            workloads.append((count, driver.id))
        if not workloads:
            return self.env["res.users"]

        _count, driver_id = min(workloads)
        return drivers.browse(driver_id)

    def _assign_driver_automatically(self):
        for order in self:
            if order.delivery_user_id:
                continue
            driver = order._select_best_driver()
            if driver:
                order.delivery_user_id = driver.id

    def _ensure_estimated_delivery_datetime(self):
        for order in self:
            if order.estimated_delivery_datetime:
                continue
            order.estimated_delivery_datetime = order._calculate_estimated_delivery()

    def _apply_dispatch_defaults(self):
        dispatch_orders = self.filtered(
            lambda order: order.state in ("confirmed", "preparing", "on_the_way")
        )
        dispatch_orders._assign_driver_automatically()
        dispatch_orders._ensure_estimated_delivery_datetime()

    def _get_delivered_datetime(self):
        self.ensure_one()
        delivered_logs = self.state_log_ids.filtered(lambda log: log.state_to == "delivered")
        delivered_logs = delivered_logs.sorted(
            key=lambda log: (log.change_datetime or fields.Datetime.now(), log.id)
        )
        if delivered_logs:
            return delivered_logs[-1].change_datetime
        return self.order_datetime or self.write_date or fields.Datetime.now()

    def _is_within_claim_window(self):
        self.ensure_one()
        if self.state != "delivered":
            return False
        hours_limit = max(1, self._get_claim_hours_limit())
        delivered_datetime = self._get_delivered_datetime()
        return fields.Datetime.now() <= delivered_datetime + timedelta(hours=hours_limit)

    @api.depends("delivery_user_id", "state")
    def _compute_delivery_user_workload(self):
        active_states = ("confirmed", "preparing", "on_the_way")
        max_concurrent = self._get_max_concurrent_orders()
        for order in self:
            if not order.delivery_user_id:
                order.delivery_user_active_count = 0
                order.delivery_user_is_overloaded = False
                continue

            domain = [
                ("delivery_user_id", "=", order.delivery_user_id.id),
                ("state", "in", active_states),
            ]
            if order.id:
                domain.append(("id", "!=", order.id))

            active_count = self.search_count(domain)
            order.delivery_user_active_count = active_count
            order.delivery_user_is_overloaded = active_count >= max_concurrent

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Fixed delivery fee for all orders.
            vals["delivery_fee"] = self._get_default_delivery_fee()
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "restaurant.delivery.order"
                ) or "Nuevo"
        orders = super().create(vals_list)
        orders._apply_dispatch_defaults()
        return orders

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.phone or self.partner_id.mobile
            self.email = self.partner_id.email
            self.delivery_address = self._get_partner_delivery_address(self.partner_id)

    @api.onchange("delivery_zone_id")
    def _onchange_delivery_zone_id(self):
        # Zones are not used for pricing in fixed-fee mode.
        if not self.estimated_delivery_datetime:
            self.estimated_delivery_datetime = self._calculate_estimated_delivery()

    @api.onchange("delivery_user_id")
    def _onchange_delivery_user_id(self):
        if not self.delivery_user_id:
            return

        max_concurrent = self._get_max_concurrent_orders()
        count = self.delivery_user_active_count
        repartidor = self.delivery_user_id
        if count >= max_concurrent:
            return {
                "warning": {
                    "title": "Repartidor con carga alta",
                    "message": f"{repartidor.name} tiene {count} pedidos activos (maximo recomendado: {max_concurrent}). Desea continuar?",
                }
            }

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
                raise UserError(_("No se puede confirmar un pedido sin direccion de entrega."))
            if not order.line_ids:
                raise UserError(_("No se puede confirmar un pedido sin lineas."))

    def _calculate_estimated_delivery(self):
        self.ensure_one()

        prep_minutes = self._get_int_config_param("restaurant.delivery_default_prep_minutes", 20)
        travel_minutes = self._get_int_config_param(
            "restaurant.delivery_default_travel_minutes", 25
        )

        if "restaurant.delivery.state.log" in self.env:
            domain = [("state", "=", "delivered")]

            delivered_orders = self.search(
                domain,
                order="order_datetime desc, id desc",
                limit=20,
            )
            valid_orders = delivered_orders.filtered(
                lambda o: o.minutes_to_prepare > 0 and o.minutes_to_deliver > 0
            )
            if len(valid_orders) >= 5:
                avg_prep = sum(valid_orders.mapped("minutes_to_prepare")) / len(valid_orders)
                avg_travel = sum(valid_orders.mapped("minutes_to_deliver")) / len(valid_orders)
                if avg_prep > 0:
                    prep_minutes = int(round(avg_prep))
                if avg_travel > 0:
                    travel_minutes = int(round(avg_travel))

        return fields.Datetime.now() + timedelta(minutes=prep_minutes + travel_minutes)

    def _validate_state_transition(self, new_state):
        state_labels = dict(self._fields["state"].selection)
        for order in self:
            allowed_states = order.ALLOWED_TRANSITIONS.get(order.state, [])
            if new_state not in allowed_states:
                raise UserError(
                    _(
                        "No se puede cambiar de '%(current)s' a '%(new)s' en el pedido %(order)s."
                    )
                    % {
                        "current": state_labels.get(order.state, order.state),
                        "new": state_labels.get(new_state, new_state),
                        "order": order.name,
                    }
                )

    def action_confirm(self):
        self._validate_state_transition("confirmed")
        is_available, unavailable_message = (
            self.env["restaurant.delivery.schedule"].is_delivery_available()
        )
        is_admin = self.env.user.has_group(
            "restaurant_casa_vieja_base.group_restaurant_administrador"
        )
        if not is_available and not is_admin:
            raise UserError(unavailable_message)
        self._validate_required_for_confirmation()
        self.write({"delivery_fee": self._get_default_delivery_fee()})
        self.write({"state": "confirmed"})
        self._apply_dispatch_defaults()

    def action_prepare(self):
        self._validate_state_transition("preparing")
        self.write({"state": "preparing"})

    def action_send(self):
        self._validate_state_transition("on_the_way")
        is_admin = self.env.user.has_group(
            "restaurant_casa_vieja_base.group_restaurant_administrador"
        )
        for order in self:
            if not is_admin and order.delivery_user_id and order.delivery_user_id != self.env.user:
                raise UserError(
                    _("Solo el repartidor asignado puede marcar este pedido como en camino.")
                )
        self.write({"state": "on_the_way"})

    def action_deliver(self):
        self._validate_state_transition("delivered")
        is_admin = self.env.user.has_group(
            "restaurant_casa_vieja_base.group_restaurant_administrador"
        )
        for order in self:
            if not is_admin and order.delivery_user_id != self.env.user:
                raise UserError(
                    _("Solo el repartidor asignado puede marcar este pedido como entregado.")
                )
        self.write({"state": "delivered"})
        for order in self:
            if not order.invoice_id and order.line_ids:
                try:
                    move = order._create_invoice_internal()
                    move.action_post()
                    order._send_invoice_notification()
                except Exception as err:
                    _logger.exception(
                        "Error creando factura automatica para pedido %s", order.id
                    )
                    raise UserError(
                        _(
                            "No se pudo generar/publicar la factura del pedido %(order)s. "
                            "Revise la configuracion contable y vuelva a intentar. "
                            "Detalle: %(detail)s"
                        )
                        % {"order": order.name, "detail": str(err)}
                    ) from err

    def _get_income_account_for_product(self, product):
        return (
            product.property_account_income_id
            or product.categ_id.property_account_income_categ_id
        )

    def _get_or_create_delivery_fee_product(self):
        template = self.env["product.template"].search(
            [
                ("name", "=", "Costo de envio"),
                ("type", "=", "service"),
            ],
            limit=1,
        )
        if not template:
            template = self.env["product.template"].create(
                {
                    "name": "Costo de envio",
                    "type": "service",
                    "sale_ok": False,
                    "purchase_ok": False,
                    "list_price": 0.0,
                }
            )
        return template.product_variant_id

    def _create_invoice_internal(self):
        self.ensure_one()
        company = self.env.company
        invoice_lines = []

        for line in self.line_ids:
            product = line.product_id
            income_account = self._get_income_account_for_product(product)
            if not income_account:
                raise UserError(
                    _("El producto %s no tiene cuenta de ingreso configurada.")
                    % product.display_name
                )
            invoice_lines.append((0, 0, {
                "product_id": product.id,
                "name": line.name or product.display_name,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "account_id": income_account.id,
                "tax_ids": [(6, 0, product.taxes_id.filtered(lambda t: t.company_id == company).ids)],
            }))

        if self.delivery_fee:
            fee_product = self._get_or_create_delivery_fee_product()
            fee_account = self._get_income_account_for_product(fee_product)
            if not fee_account:
                raise UserError(
                    _("El producto Costo de envio no tiene cuenta de ingreso configurada.")
                )
            invoice_lines.append((0, 0, {
                "product_id": fee_product.id,
                "name": _("Costo de envio"),
                "quantity": 1.0,
                "price_unit": self.delivery_fee,
                "account_id": fee_account.id,
                "tax_ids": [(6, 0, fee_product.taxes_id.filtered(lambda t: t.company_id == company).ids)],
            }))

        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_line_ids": invoice_lines,
            "delivery_order_id": self.id,
        })
        self.invoice_id = move.id
        return move

    def action_create_invoice(self):
        self.ensure_one()
        if self.state != "delivered":
            raise UserError(_("Solo se puede facturar un pedido entregado."))
        if self.invoice_id:
            raise UserError(_("Este pedido ya tiene una factura asociada."))
        if not self.line_ids:
            raise UserError(_("No se puede crear factura sin lineas de pedido."))
        move = self._create_invoice_internal()
        return {
            "type": "ir.actions.act_window",
            "name": _("Factura"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }

    def _send_invoice_notification(self):
        self.ensure_one()
        if not self.invoice_id:
            return
        is_enabled = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.delivery_send_status_emails", "True")
        )
        if str(is_enabled).strip().lower() not in ("1", "true", "yes", "y", "on"):
            return
        partner_email = self.email or self.partner_id.email
        if not partner_email:
            return
        template = self.env.ref(self.INVOICE_MAIL_TEMPLATE, raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)

    def action_register_payment(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Este pedido no tiene factura asociada."))
        if self.invoice_id.state == "draft":
            raise UserError(_("La factura debe estar confirmada antes de registrar un pago."))
        return self.invoice_id.action_register_payment()

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Este pedido no tiene factura asociada."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Factura"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.invoice_id.id,
            "target": "current",
        }

    def _sync_sale_order_state(self):
        if self.env.context.get("skip_delivery_sale_sync"):
            return
        for order in self.filtered("sale_order_id"):
            sale_order = order.sale_order_id.sudo()
            if order.state == "cancelled" and sale_order.state != "cancel":
                sale_order.with_context(skip_sale_delivery_sync=True).action_cancel()
            elif order.state == "delivered" and sale_order.state in ("draft", "sent"):
                sale_order.with_context(skip_sale_delivery_sync=True).action_confirm()

    def _send_status_notification(self, new_state):
        self.ensure_one()

        is_enabled = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.delivery_send_status_emails", "True")
        )
        if str(is_enabled).strip().lower() not in ("1", "true", "yes", "y", "on"):
            return

        partner_email = self.email or self.partner_id.email
        if not partner_email:
            return

        template_xmlid = self.STATE_MAIL_TEMPLATES.get(new_state)
        if not template_xmlid:
            return

        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)

    def write(self, vals):
        self._ensure_driver_write_restrictions(vals)
        self._ensure_not_locked_for_update(vals)

        previous_states = {}
        if "state" in vals:
            previous_states = {order.id: order.state for order in self}

        res = super().write(vals)
        if "state" in vals:
            self._sync_sale_order_state()
            self._apply_dispatch_defaults()
            log_values = []
            changed_records = []
            for order in self:
                old_state = previous_states.get(order.id)
                if old_state == order.state:
                    continue
                changed_records.append((order, order.state))
                log_values.append(
                    {
                        "delivery_order_id": order.id,
                        "state_from": old_state,
                        "state_to": order.state,
                    }
                )
            if log_values:
                self.env["restaurant.delivery.state.log"].sudo().create(log_values)
            for order, new_state in changed_records:
                try:
                    order._send_status_notification(new_state)
                except Exception:
                    _logger.exception(
                        "Error enviando notificacion de estado '%s' para pedido %s",
                        new_state,
                        order.id,
                    )
        return res

    def _ensure_driver_write_restrictions(self, vals):
        if not vals:
            return
        if self.env.context.get("allow_delivery_driver_write"):
            return

        user = self.env.user
        is_driver = user.has_group("restaurant_casa_vieja_base.group_restaurant_repartidor")
        if not is_driver:
            return

        is_admin = user.has_group("restaurant_casa_vieja_base.group_restaurant_administrador")
        is_admin_ops = user.has_group("restaurant_casa_vieja_base.group_restaurant_administracion")
        if is_admin or is_admin_ops:
            return

        blocked_fields = set(vals) - self.DRIVER_WRITE_ALLOWED_FIELDS
        if not blocked_fields:
            return

        raise UserError(
            _(
                "Como repartidor solo puede actualizar el estado del pedido. "
                "Campos bloqueados: %(fields)s"
            )
            % {"fields": ", ".join(sorted(blocked_fields))}
        )

    def _ensure_not_locked_for_update(self, vals):
        if self.env.context.get("allow_locked_delivery_write"):
            return

        blocked_fields = set(vals) & self.LOCKED_WRITE_BLOCKED_FIELDS
        if not blocked_fields:
            return

        locked_orders = self.filtered(lambda order: order.state in self.LOCKED_STATES)
        if not locked_orders:
            return

        order_refs = ", ".join(locked_orders.mapped("name"))
        fields_list = ", ".join(sorted(blocked_fields))
        raise UserError(
            _(
                "No se pueden modificar los campos %(fields)s en pedidos cerrados (%(orders)s)."
            )
            % {"fields": fields_list, "orders": order_refs}
        )

    def _action_cancel_direct(self):
        self.write({"state": "cancelled"})

    def action_cancel(self):
        if not self:
            return

        if len(self) > 1 and any(
            order.state in ("preparing", "on_the_way") for order in self
        ):
            raise UserError(
                _(
                    "Para cancelar pedidos en preparacion o en camino, hagalo de forma individual."
                )
            )

        if len(self) == 1 and self.state in ("preparing", "on_the_way"):
            self._validate_state_transition("cancelled")
            return {
                "type": "ir.actions.act_window",
                "res_model": "restaurant.delivery.cancel.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {"default_delivery_order_id": self.id},
            }

        self._validate_state_transition("cancelled")
        self.write({"cancel_reason": False})
        self._action_cancel_direct()

    def action_reset_to_draft(self):
        self._validate_state_transition("draft")
        self.write({"state": "draft"})

    def action_recalculate_eta(self):
        for order in self:
            order.estimated_delivery_datetime = order._calculate_estimated_delivery()

    def action_view_claims(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reclamos"),
            "res_model": "restaurant.delivery.claim",
            "view_mode": "list,kanban,form",
            "domain": [("delivery_order_id", "=", self.id)],
            "context": {"default_delivery_order_id": self.id},
        }
