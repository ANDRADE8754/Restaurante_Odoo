from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TableReservation(models.Model):
    _name = "restaurant.table.reservation"
    _description = "Reserva de Mesa"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "reservation_start desc, name desc"

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
    table_id = fields.Many2one(
        comodel_name="restaurant.table",
        string="Mesa",
        required=True,
        tracking=True,
    )
    reservation_start = fields.Datetime(
        string="Inicio",
        required=True,
        tracking=True,
    )
    reservation_end = fields.Datetime(
        string="Fin",
        required=True,
        tracking=True,
    )
    guest_count = fields.Integer(
        string="Número de comensales",
        required=True,
        default=1,
    )
    special_occasion = fields.Selection(
        selection=[
            ("none", "Ninguna"),
            ("birthday", "Cumpleaños"),
            ("anniversary", "Aniversario"),
            ("business", "Reunión de trabajo"),
            ("family", "Reunión familiar"),
            ("other", "Otra"),
        ],
        string="Ocasión especial",
        default="none",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Pendiente"),
            ("confirmed", "Confirmada"),
            ("in_progress", "En curso"),
            ("done", "Finalizada"),
            ("cancelled", "Cancelada"),
            ("no_show", "No asistió"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsable",
        default=lambda self: self.env.user,
    )
    crm_lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="Oportunidad CRM",
    )
    notes = fields.Text(string="Observaciones")
    duration_hours = fields.Float(
        string="Duración en horas",
        compute="_compute_duration_hours",
    )

    @api.depends("reservation_start", "reservation_end")
    def _compute_duration_hours(self):
        for reservation in self:
            if reservation.reservation_start and reservation.reservation_end:
                duration = reservation.reservation_end - reservation.reservation_start
                reservation.duration_hours = duration.total_seconds() / 3600
            else:
                reservation.duration_hours = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "restaurant.table.reservation"
                ) or "Nuevo"
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if vals.get("state") == "confirmed":
            self._validate_required_for_confirmation()
        return result

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.phone or self.partner_id.mobile
            self.email = self.partner_id.email

    @api.onchange("table_id", "guest_count")
    def _onchange_table_capacity(self):
        if (
            self.table_id
            and self.guest_count
            and self.guest_count > self.table_id.capacity
        ):
            return {
                "warning": {
                    "title": _("Capacidad excedida"),
                    "message": _(
                        "La mesa seleccionada tiene capacidad para %(capacity)s personas."
                    )
                    % {"capacity": self.table_id.capacity},
                }
            }
        return {}

    @api.constrains("guest_count")
    def _check_guest_count(self):
        for reservation in self:
            if reservation.guest_count <= 0:
                raise ValidationError(_("El número de comensales debe ser mayor que cero."))

    @api.constrains("reservation_start", "reservation_end")
    def _check_reservation_dates(self):
        for reservation in self:
            if (
                reservation.reservation_start
                and reservation.reservation_end
                and reservation.reservation_end <= reservation.reservation_start
            ):
                raise ValidationError(_("La fecha de fin debe ser posterior a la fecha de inicio."))

    @api.constrains("guest_count", "table_id")
    def _check_table_capacity(self):
        for reservation in self:
            if (
                reservation.table_id
                and reservation.guest_count
                and reservation.guest_count > reservation.table_id.capacity
            ):
                raise ValidationError(
                    _("El número de comensales no puede superar la capacidad de la mesa.")
                )

    @api.constrains("table_id", "reservation_start", "reservation_end", "state")
    def _check_overlapping_reservations(self):
        active_states = ("draft", "confirmed", "in_progress", "done")
        for reservation in self:
            if (
                not reservation.table_id
                or not reservation.reservation_start
                or not reservation.reservation_end
                or reservation.state not in active_states
            ):
                continue

            overlapping_reservation = self.search(
                [
                    ("id", "!=", reservation.id),
                    ("table_id", "=", reservation.table_id.id),
                    ("state", "not in", ["cancelled", "no_show"]),
                    ("reservation_start", "<", reservation.reservation_end),
                    ("reservation_end", ">", reservation.reservation_start),
                ],
                limit=1,
            )
            if overlapping_reservation:
                raise ValidationError(
                    _(
                        "La mesa ya tiene una reserva en ese horario: %(reservation)s."
                    )
                    % {"reservation": overlapping_reservation.display_name}
                )

    def _validate_required_for_confirmation(self):
        for reservation in self:
            missing_fields = []
            if not reservation.partner_id:
                missing_fields.append(_("Cliente"))
            if not reservation.table_id:
                missing_fields.append(_("Mesa"))
            if not reservation.reservation_start:
                missing_fields.append(_("Inicio"))
            if not reservation.reservation_end:
                missing_fields.append(_("Fin"))
            if not reservation.guest_count:
                missing_fields.append(_("Número de comensales"))
            if missing_fields:
                raise UserError(
                    _("No se puede confirmar la reserva. Faltan datos: %s.")
                    % ", ".join(missing_fields)
                )

    def action_confirm(self):
        self._validate_required_for_confirmation()
        self.write({"state": "confirmed"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_no_show(self):
        self.write({"state": "no_show"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
