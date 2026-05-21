from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TableReservation(models.Model):
    _name = "restaurant.table.reservation"
    _description = "Reserva de Mesa"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc, name desc"

    ACTIVE_STATES = ("draft", "confirmed", "seated")
    CLOSED_STATES = ("done", "cancelled", "no_show")
    LOCKED_WRITE_BLOCKED_FIELDS = {
        "partner_id",
        "customer_name",
        "customer_phone",
        "customer_email",
        "table_id",
        "requested_area",
        "start_datetime",
        "end_datetime",
        "duration_minutes",
        "guest_count",
        "source_channel",
        "source_reference",
        "pos_order_id",
        "notes",
        "customer_note",
        "cancellation_reason",
        "user_id",
        "active",
        "company_id",
    }

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        tracking=True,
    )
    customer_name = fields.Char(string="Nombre del cliente", tracking=True)
    customer_phone = fields.Char(string="Telefono", tracking=True)
    customer_email = fields.Char(string="Correo electronico", tracking=True)

    table_id = fields.Many2one(
        comodel_name="restaurant.table",
        string="Mesa",
        tracking=True,
        index=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    requested_area = fields.Selection(
        selection=[
            ("interior", "Interior"),
            ("terraza", "Terraza"),
            ("jardin", "Jardin"),
            ("salon", "Salon principal"),
            ("otro", "Otro"),
        ],
        string="Zona solicitada",
    )
    reservation_date = fields.Date(
        string="Fecha de reserva",
        compute="_compute_reservation_date",
        store=True,
        index=True,
    )
    start_datetime = fields.Datetime(
        string="Inicio",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    end_datetime = fields.Datetime(
        string="Fin",
        required=True,
        tracking=True,
    )
    duration_minutes = fields.Integer(
        string="Duracion (minutos)",
        compute="_compute_duration_minutes",
        inverse="_inverse_duration_minutes",
        store=True,
    )
    guest_count = fields.Integer(
        string="Numero de personas",
        default=2,
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("confirmed", "Confirmada"),
            ("seated", "Cliente sentado"),
            ("done", "Finalizada"),
            ("cancelled", "Cancelada"),
            ("no_show", "No asistio"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    source_channel = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("website", "Sitio web"),
            ("pos", "Punto de venta"),
        ],
        string="Origen",
        default="manual",
        required=True,
        tracking=True,
        index=True,
    )
    source_reference = fields.Char(
        string="Referencia externa",
        copy=False,
        index=True,
        help="Referencia tecnica para integraciones web/POS externas.",
    )

    pos_order_id = fields.Many2one(
        comodel_name="pos.order",
        string="Pedido POS",
        copy=False,
        index=True,
    )

    notes = fields.Text(string="Notas internas")
    customer_note = fields.Text(string="Nota del cliente")
    cancellation_reason = fields.Text(string="Motivo de cancelacion")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compania",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    active = fields.Boolean(string="Activa", default=True)

    display_name = fields.Char(
        string="Nombre mostrado",
        compute="_compute_display_name",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("start_datetime")
    def _compute_reservation_date(self):
        for rec in self:
            rec.reservation_date = (
                fields.Datetime.context_timestamp(rec, rec.start_datetime).date()
                if rec.start_datetime
                else False
            )

    @api.depends("start_datetime", "end_datetime")
    def _compute_duration_minutes(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime > rec.start_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration_minutes = max(1, int(delta.total_seconds() // 60))
            else:
                rec.duration_minutes = 120

    def _inverse_duration_minutes(self):
        for rec in self:
            if not rec.start_datetime:
                continue
            minutes = max(1, int(rec.duration_minutes or 120))
            rec.end_datetime = fields.Datetime.add(rec.start_datetime, minutes=minutes)

    @api.depends("name", "partner_id", "customer_name", "table_id", "start_datetime")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._prepare_display_name()

    def _prepare_display_name(self):
        self.ensure_one()
        parts = [self.name or _("Nuevo")]
        client = self.partner_id.display_name or self.customer_name
        if client:
            parts.append(client)
        if self.table_id:
            table_label = self.table_id.name or self.table_id.display_name
            if table_label:
                parts.append(table_label)
        return " - ".join(parts)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            if not self.customer_name:
                self.customer_name = self.partner_id.name
            if not self.customer_phone:
                self.customer_phone = self.partner_id.phone or self.partner_id.mobile
            if not self.customer_email:
                self.customer_email = self.partner_id.email

    @api.onchange("table_id")
    def _onchange_table_id(self):
        if self.table_id and not self.requested_area:
            self.requested_area = self.table_id.location_area

    @api.onchange("start_datetime")
    def _onchange_start_datetime(self):
        if self.start_datetime and (
            not self.end_datetime or self.end_datetime <= self.start_datetime
        ):
            self.end_datetime = fields.Datetime.add(self.start_datetime, hours=2)

    @api.onchange("duration_minutes")
    def _onchange_duration_minutes(self):
        if self.start_datetime and self.duration_minutes:
            self.end_datetime = fields.Datetime.add(
                self.start_datetime, minutes=max(1, int(self.duration_minutes))
            )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("start_datetime", "end_datetime")
    def _check_datetime_range(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime <= rec.start_datetime:
                raise ValidationError(
                    _("La fecha/hora de fin debe ser posterior al inicio de la reserva.")
                )

    @api.constrains("guest_count")
    def _check_guest_count(self):
        for rec in self:
            if rec.guest_count <= 0:
                raise ValidationError(_("El numero de personas debe ser mayor que cero."))

    @api.constrains("company_id", "table_id")
    def _check_company_table_consistency(self):
        for rec in self:
            if rec.table_id and rec.company_id != rec.table_id.company_id:
                raise ValidationError(
                    _(
                        "La mesa %(table)s pertenece a %(table_company)s y no coincide "
                        "con la compania de la reserva %(reservation_company)s."
                    )
                    % {
                        "table": rec.table_id.display_name,
                        "table_company": rec.table_id.company_id.display_name,
                        "reservation_company": rec.company_id.display_name,
                    }
                )

    @api.constrains("guest_count", "table_id")
    def _check_table_capacity(self):
        if self.env.context.get("skip_table_capacity_check"):
            return
        for rec in self:
            if rec.table_id and rec.table_id.capacity and rec.guest_count > rec.table_id.capacity:
                raise ValidationError(
                    _(
                        "El numero de personas (%(guests)s) supera la capacidad "
                        "de la mesa %(table)s (%(cap)s)."
                    )
                    % {
                        "guests": rec.guest_count,
                        "table": rec.table_id.name,
                        "cap": rec.table_id.capacity,
                    }
                )

    @api.constrains("table_id", "start_datetime", "end_datetime", "state")
    def _check_overlapping(self):
        for rec in self:
            if rec.state not in self.ACTIVE_STATES:
                continue
            rec._check_table_availability()

    @api.constrains("table_id", "state")
    def _check_table_active(self):
        for rec in self:
            if (
                rec.state in ("confirmed", "seated")
                and rec.table_id
                and not rec.table_id.active
            ):
                raise ValidationError(
                    _("No es posible usar una mesa inactiva en una reserva confirmada.")
                )

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------
    @api.model
    def _normalize_reservation_window(
        self, start_datetime, end_datetime=False, duration_minutes=120
    ):
        start_dt = fields.Datetime.to_datetime(start_datetime) if start_datetime else False
        if not start_dt:
            raise ValidationError(_("Debe indicar fecha/hora de inicio de la reserva."))

        if end_datetime:
            end_dt = fields.Datetime.to_datetime(end_datetime)
        else:
            duration = max(1, int(duration_minutes or 120))
            end_dt = fields.Datetime.add(start_dt, minutes=duration)

        if not end_dt or end_dt <= start_dt:
            raise ValidationError(
                _("La fecha/hora de fin debe ser posterior al inicio de la reserva.")
            )
        return start_dt, end_dt

    @api.model
    def _get_overlap_domain(self, table_ids, start_dt, end_dt, exclude_reservation_id=False):
        domain = [
            ("table_id", "in", table_ids),
            ("state", "in", list(self.ACTIVE_STATES)),
            ("start_datetime", "<", end_dt),
            ("end_datetime", ">", start_dt),
        ]
        if exclude_reservation_id:
            domain.append(("id", "!=", exclude_reservation_id))
        return domain

    def _get_overlapping_reservations(self):
        self.ensure_one()
        if not self.table_id or not self.start_datetime or not self.end_datetime:
            return self.env["restaurant.table.reservation"]
        domain = self._get_overlap_domain(
            [self.table_id.id],
            self.start_datetime,
            self.end_datetime,
            exclude_reservation_id=self.id,
        )
        return self.search(domain)

    def _check_table_availability(self):
        for rec in self:
            overlapping = rec._get_overlapping_reservations()
            if overlapping:
                raise ValidationError(
                    _(
                        "La mesa %(table)s ya tiene una reserva activa en ese horario "
                        "(%(ref)s)."
                    )
                    % {
                        "table": rec.table_id.name,
                        "ref": ", ".join(overlapping.mapped("name")),
                    }
                )

    @api.model
    def get_available_tables(
        self,
        start_datetime,
        end_datetime=False,
        guest_count=1,
        location_area=False,
        company_id=False,
        exclude_reservation_id=False,
    ):
        start_dt, end_dt = self._normalize_reservation_window(start_datetime, end_datetime)
        try:
            guest_count_int = max(1, int(guest_count or 1))
        except (TypeError, ValueError):
            guest_count_int = 1
        company = (
            self.env["res.company"].browse(company_id).exists()
            if company_id
            else self.env.company
        )
        if not company:
            company = self.env.company

        table_domain = [
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("capacity", ">=", guest_count_int),
        ]
        if location_area:
            table_domain.append(("location_area", "=", location_area))
        tables = self.env["restaurant.table"].search(table_domain, order="capacity asc, name asc")
        if not tables:
            return tables

        overlap_domain = self._get_overlap_domain(
            tables.ids,
            start_dt,
            end_dt,
            exclude_reservation_id=exclude_reservation_id,
        )
        taken_table_ids = set(self.search(overlap_domain).mapped("table_id").ids)
        return tables.filtered(lambda table: table.id not in taken_table_ids)

    @api.model
    def is_table_available(
        self,
        table_id,
        start_datetime,
        end_datetime=False,
        exclude_reservation_id=False,
    ):
        table = self.env["restaurant.table"].browse(table_id).exists()
        if not table:
            return False
        start_dt, end_dt = self._normalize_reservation_window(start_datetime, end_datetime)
        overlap_domain = self._get_overlap_domain(
            [table.id],
            start_dt,
            end_dt,
            exclude_reservation_id=exclude_reservation_id,
        )
        return self.search_count(overlap_domain) == 0

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "restaurant.table.reservation"
                ) or _("Nuevo")

            start_dt = fields.Datetime.to_datetime(vals.get("start_datetime")) if vals.get(
                "start_datetime"
            ) else fields.Datetime.now()
            if not vals.get("start_datetime"):
                vals["start_datetime"] = fields.Datetime.to_string(start_dt)

            if not vals.get("end_datetime"):
                duration = max(1, int(vals.get("duration_minutes") or 120))
                vals["end_datetime"] = fields.Datetime.to_string(
                    fields.Datetime.add(start_dt, minutes=duration)
                )

            if vals.get("table_id") and not vals.get("requested_area"):
                table = self.env["restaurant.table"].browse(vals["table_id"]).exists()
                if table:
                    vals["requested_area"] = table.location_area

        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("allow_locked_reservation_write"):
            blocked = self.LOCKED_WRITE_BLOCKED_FIELDS.intersection(vals.keys())
            if blocked:
                for rec in self:
                    if rec.state in self.CLOSED_STATES:
                        raise UserError(
                            _(
                                "No se pueden modificar los campos %(fields)s en una "
                                "reserva en estado %(state)s."
                            )
                            % {
                                "fields": ", ".join(sorted(blocked)),
                                "state": dict(self._fields["state"].selection).get(rec.state),
                            }
                        )
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancelled"):
                raise UserError(
                    _(
                        "Solo se pueden eliminar reservas en estado Borrador o "
                        "Cancelada. Estado actual: %s"
                    )
                    % dict(self._fields["state"].selection).get(rec.state)
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Helpers for integration
    # ------------------------------------------------------------------
    @api.model
    def prepare_website_reservation_vals(self, vals):
        vals = dict(vals or {})
        vals["source_channel"] = "website"
        return vals

    @api.model
    def prepare_pos_reservation_vals(self, vals):
        vals = dict(vals or {})
        vals["source_channel"] = vals.get("source_channel") or "pos"
        return vals

    @api.model
    def find_linkable_reservation_for_pos(self, reference, company_id=False):
        """Busca una reserva activa utilizable desde POS por referencia."""
        query = (reference or "").strip()
        if not query:
            return False

        domain = [
            ("state", "in", list(self.ACTIVE_STATES)),
            ("table_id", "!=", False),
            "|",
            ("name", "ilike", query),
            ("source_reference", "ilike", query),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        reservation = self.search(domain, order="start_datetime asc, id asc", limit=1)
        if not reservation:
            return False
        return {
            "id": reservation.id,
            "name": reservation.name,
            "table_name": reservation.table_id.display_name,
            "state": reservation.state,
            "start_datetime": fields.Datetime.to_string(reservation.start_datetime),
        }

    @api.model
    def get_active_reservations_for_pos(self, company_id=False, limit=30):
        """Lista reservas activas para seleccion rapida desde POS."""
        try:
            limit_int = max(1, min(int(limit or 30), 100))
        except (TypeError, ValueError):
            limit_int = 30

        domain = [
            ("state", "in", list(self.ACTIVE_STATES)),
            ("table_id", "!=", False),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        reservations = self.search(domain, order="start_datetime asc, id asc", limit=limit_int)
        payload = []
        for reservation in reservations:
            payload.append(
                {
                    "id": reservation.id,
                    "name": reservation.name,
                    "table_name": reservation.table_id.display_name or reservation.table_id.name,
                    "state": reservation.state,
                    "start_datetime": fields.Datetime.to_string(reservation.start_datetime),
                    "customer_name": reservation.customer_name or reservation.partner_id.name or "",
                }
            )
        return payload

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state not in ("draft",):
                raise UserError(_("Solo se puede confirmar una reserva en borrador."))
            if not rec.table_id:
                raise UserError(_("Debe asignar una mesa antes de confirmar la reserva."))
            rec._check_table_availability()
            rec.state = "confirmed"
        return True

    def action_seat(self):
        for rec in self:
            if rec.state not in ("confirmed",):
                raise UserError(
                    _("Solo se puede sentar a un cliente desde una reserva confirmada.")
                )
            rec.state = "seated"
        return True

    def action_done(self):
        for rec in self:
            if rec.state not in ("seated", "confirmed"):
                raise UserError(
                    _("Solo se puede finalizar una reserva confirmada o con cliente sentado.")
                )
            rec.state = "done"
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ("done",):
                raise UserError(_("No se puede cancelar una reserva ya finalizada."))
            rec.state = "cancelled"
        return True

    def action_no_show(self):
        for rec in self:
            if rec.state not in ("confirmed",):
                raise UserError(
                    _("Solo se puede marcar como No asistio una reserva confirmada.")
                )
            rec.state = "no_show"
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("No se puede regresar a borrador una reserva finalizada."))
            rec.state = "draft"
        return True
