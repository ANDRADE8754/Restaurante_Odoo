import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    # Estados de pos.order considerados "cerrados" para disparar el cierre de la reserva.
    RESERVATION_CLOSE_STATES = ("paid", "done", "invoiced")
    # Ventana temporal (+/- 24h) en la que se considera razonable vincular una reserva.
    RESERVATION_LINKABLE_WINDOW_SECONDS = 24 * 60 * 60

    reservation_id = fields.Many2one(
        comodel_name="restaurant.table.reservation",
        string="Reserva de mesa",
        copy=False,
        index=True,
        ondelete="set null",
        help="Reserva del restaurante vinculada a esta orden POS.",
    )
    reservation_state = fields.Selection(
        related="reservation_id.state",
        string="Estado de la reserva",
        readonly=True,
    )
    reservation_table_id = fields.Many2one(
        related="reservation_id.table_id",
        string="Mesa de la reserva",
        readonly=True,
    )
    reservation_guest_count = fields.Integer(
        related="reservation_id.guest_count",
        string="Comensales reserva",
        readonly=True,
    )

    _sql_constraints = [
        (
            "pos_order_reservation_uniq",
            "unique(reservation_id)",
            "Esta reserva ya esta vinculada a otra orden POS.",
        ),
    ]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("reservation_id")
    def _check_reservation_link_constraint(self):
        for order in self:
            if order.reservation_id:
                order._check_reservation_can_be_linked(order.reservation_id)

    def _check_reservation_can_be_linked(self, reservation):
        """Valida que la reserva indicada puede vincularse a esta orden POS.

        Reglas:
        - Reserva existente y activa.
        - Estado en (draft, confirmed, seated).
        - Tiene mesa asignada.
        - Misma compania que la orden POS.
        - No vinculada a otra orden POS.
        - Ventana de fechas razonable (default +/- 24h) salvo bypass por contexto
          'skip_reservation_date_check'.
        """
        self.ensure_one()
        Reservation = self.env["restaurant.table.reservation"]
        if not reservation or not reservation.exists():
            raise UserError(_("Debe indicar una reserva valida para vincular."))
        if not reservation.active:
            raise UserError(_("La reserva %s esta archivada.") % reservation.name)
        if reservation.state not in Reservation.ACTIVE_STATES:
            raise UserError(
                _("La reserva %(name)s no esta activa (estado: %(state)s).")
                % {
                    "name": reservation.name,
                    "state": dict(reservation._fields["state"].selection).get(
                        reservation.state
                    ),
                }
            )
        if not reservation.table_id:
            raise UserError(
                _(
                    "La reserva %s no tiene mesa asignada y no puede vincularse al POS."
                )
                % reservation.name
            )
        if (
            self.company_id
            and reservation.company_id
            and reservation.company_id != self.company_id
        ):
            raise UserError(
                _(
                    "La reserva %(res)s pertenece a la compania %(c1)s y la orden POS "
                    "a %(c2)s."
                )
                % {
                    "res": reservation.name,
                    "c1": reservation.company_id.display_name,
                    "c2": self.company_id.display_name,
                }
            )
        other_pos = self.search(
            [("reservation_id", "=", reservation.id), ("id", "!=", self.id)],
            limit=1,
        )
        if other_pos:
            raise UserError(
                _("La reserva %(res)s ya esta vinculada a la orden POS %(order)s.")
                % {"res": reservation.name, "order": other_pos.display_name}
            )
        if reservation.pos_order_id and reservation.pos_order_id != self:
            raise UserError(
                _("La reserva %(res)s ya tiene una orden POS asociada (%(order)s).")
                % {
                    "res": reservation.name,
                    "order": reservation.pos_order_id.display_name,
                }
            )
        if (
            reservation.start_datetime
            and not self.env.context.get("skip_reservation_date_check")
        ):
            now = fields.Datetime.now()
            delta = abs((reservation.start_datetime - now).total_seconds())
            if delta > self.RESERVATION_LINKABLE_WINDOW_SECONDS:
                raise UserError(
                    _(
                        "La reserva %s no esta dentro de la ventana de vinculacion "
                        "(24h respecto a su inicio)."
                    )
                    % reservation.name
                )
        return True

    # ------------------------------------------------------------------
    # Sync helpers
    # ------------------------------------------------------------------
    def _sync_reservation_on_link(self):
        """Sincroniza back-link y estado de la reserva cuando se vincula al POS."""
        self.ensure_one()
        reservation = self.reservation_id
        if not reservation:
            return False
        new_vals = {}
        if reservation.pos_order_id.id != self.id:
            new_vals["pos_order_id"] = self.id
        if reservation.source_channel == "manual":
            new_vals["source_channel"] = "pos"
        if reservation.state in ("draft", "confirmed"):
            new_vals["state"] = "seated"
        if new_vals:
            reservation.with_context(allow_locked_reservation_write=True).write(new_vals)
        return True

    def _mark_reservation_done_on_payment(self):
        """Cierra la reserva vinculada cuando la orden POS pasa a estado cerrado.

        Solo cambia la reserva a 'done' si esta en 'confirmed' o 'seated'.
        Nunca cierra una reserva ya en estado done/cancelled/no_show.
        """
        self.ensure_one()
        reservation = self.reservation_id
        if not reservation:
            return False
        if reservation.state in ("seated", "confirmed"):
            reservation.with_context(allow_locked_reservation_write=True).write(
                {"state": "done"}
            )
            return True
        return False

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------
    def action_link_reservation(self, reservation_id):
        """Vincula una reserva a la orden POS actual.

        Pensado para usarse desde el formulario administrativo o desde RPC
        (futuro frontend POS). Aplica todas las validaciones.
        """
        self.ensure_one()
        reservation = self.env["restaurant.table.reservation"].browse(reservation_id)
        self._check_reservation_can_be_linked(reservation)
        self.write({"reservation_id": reservation.id})
        return True

    def action_unlink_reservation(self):
        """Desvincula la reserva sin alterar su estado."""
        for order in self:
            reservation = order.reservation_id
            if reservation and reservation.pos_order_id == order:
                reservation.with_context(
                    allow_locked_reservation_write=True
                ).write({"pos_order_id": False})
            order.reservation_id = False
        return True

    def action_mark_reservation_done(self):
        """Accion manual para forzar el cierre de la reserva vinculada.

        Util si el flujo automatico de cierre no se dispara (por ejemplo
        ordenes creadas en estado 'paid' antes de que existiera el modulo).
        """
        for order in self:
            order._mark_reservation_done_on_payment()
        return True

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.reservation_id:
                order._sync_reservation_on_link()
                if order.state in self.RESERVATION_CLOSE_STATES:
                    order._mark_reservation_done_on_payment()
        return orders

    def write(self, vals):
        previous_links = {order.id: order.reservation_id for order in self}
        res = super().write(vals)
        if "reservation_id" in vals:
            for order in self:
                old_link = previous_links.get(order.id)
                if old_link and old_link != order.reservation_id:
                    if old_link.pos_order_id == order:
                        old_link.with_context(
                            allow_locked_reservation_write=True
                        ).write({"pos_order_id": False})
                if order.reservation_id:
                    order._sync_reservation_on_link()
                    if order.state in self.RESERVATION_CLOSE_STATES:
                        order._mark_reservation_done_on_payment()
        if vals.get("state") in self.RESERVATION_CLOSE_STATES:
            for order in self:
                if order.reservation_id:
                    order._mark_reservation_done_on_payment()
        return res

    def unlink(self):
        for order in self:
            reservation = order.reservation_id
            if reservation and reservation.pos_order_id == order:
                reservation.with_context(
                    allow_locked_reservation_write=True
                ).write({"pos_order_id": False})
        return super().unlink()


class TableReservation(models.Model):
    _inherit = "restaurant.table.reservation"

    def action_open_pos_order(self):
        """Abre la orden POS vinculada (boton/accion desde el backend)."""
        self.ensure_one()
        if not self.pos_order_id:
            raise UserError(_("Esta reserva no tiene una orden POS vinculada."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Orden POS"),
            "res_model": "pos.order",
            "view_mode": "form",
            "res_id": self.pos_order_id.id,
            "target": "current",
        }
