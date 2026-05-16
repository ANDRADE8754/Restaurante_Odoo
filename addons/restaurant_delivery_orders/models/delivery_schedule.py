from datetime import datetime

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DeliverySchedule(models.Model):
    _name = "restaurant.delivery.schedule"
    _description = "Horario de atención delivery"
    _order = "day_of_week"

    DAY_SELECTION = [
        ("0", "Lunes"),
        ("1", "Martes"),
        ("2", "Miércoles"),
        ("3", "Jueves"),
        ("4", "Viernes"),
        ("5", "Sábado"),
        ("6", "Domingo"),
    ]

    name = fields.Char(
        string="Horario",
        compute="_compute_name",
        store=True,
    )
    day_of_week = fields.Selection(
        selection=DAY_SELECTION,
        string="Día",
        required=True,
    )
    hour_from = fields.Float(
        string="Hora apertura",
        required=True,
        default=11.0,
    )
    hour_to = fields.Float(
        string="Hora cierre",
        required=True,
        default=22.0,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "day_company_uniq",
            "unique(day_of_week, company_id)",
            "Ya existe un horario configurado para este día en la compañía.",
        ),
    ]

    @api.depends("day_of_week", "hour_from", "hour_to")
    def _compute_name(self):
        days = dict(self.DAY_SELECTION)
        for rec in self:
            day_label = days.get(rec.day_of_week, "")
            rec.name = _("%s: %s - %s") % (
                day_label,
                rec._format_float_hour(rec.hour_from),
                rec._format_float_hour(rec.hour_to),
            )

    @api.constrains("hour_from", "hour_to")
    def _check_hours(self):
        for rec in self:
            if rec.hour_from < 0.0 or rec.hour_from > 24.0:
                raise ValidationError(_("La hora de apertura debe estar entre 0.0 y 24.0."))
            if rec.hour_to < 0.0 or rec.hour_to > 24.0:
                raise ValidationError(_("La hora de cierre debe estar entre 0.0 y 24.0."))
            if rec.hour_from >= rec.hour_to:
                raise ValidationError(
                    _("La hora de apertura debe ser menor que la hora de cierre.")
                )

    @api.model
    def _format_float_hour(self, hour_value):
        hour_value = hour_value or 0.0
        total_minutes = int(round(hour_value * 60))
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    @api.model
    def is_delivery_available(self, dt=None):
        company = self.env.company
        tz_name = (
            getattr(company, "tz", False)
            or company.partner_id.tz
            or "America/Guayaquil"
        )
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("America/Guayaquil")

        if dt is None:
            dt_value = fields.Datetime.to_datetime(fields.Datetime.now())
        else:
            dt_value = fields.Datetime.to_datetime(dt)

        if not dt_value:
            dt_value = datetime.utcnow()

        if dt_value.tzinfo:
            dt_utc = dt_value.astimezone(pytz.utc)
        else:
            dt_utc = pytz.utc.localize(dt_value)

        local_dt = dt_utc.astimezone(tz)
        weekday = str(local_dt.weekday())
        day_labels = dict(self.DAY_SELECTION)
        day_label = day_labels.get(weekday, _("día seleccionado"))

        schedule = self.search(
            [
                ("company_id", "=", company.id),
                ("day_of_week", "=", weekday),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not schedule:
            return False, _("No hay servicio de delivery los %s") % day_label

        current_hour = (
            local_dt.hour + (local_dt.minute / 60.0) + (local_dt.second / 3600.0)
        )
        if current_hour < schedule.hour_from or current_hour > schedule.hour_to:
            return (
                False,
                _("Delivery disponible de %s a %s")
                % (
                    self._format_float_hour(schedule.hour_from),
                    self._format_float_hour(schedule.hour_to),
                ),
            )
        return True, ""
