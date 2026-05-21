import logging
import re
from datetime import datetime, timedelta
from uuid import uuid4

import pytz
from pytz.exceptions import AmbiguousTimeError, NonExistentTimeError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class WebsiteTableReservationController(Controller):
    DEFAULT_RESERVATION_MINUTES = 90
    SESSION_CONFIRM_KEY = "restaurant_table_reservation_last_confirmation"
    DEFAULT_WEBSITE_TZ = "America/Guayaquil"
    EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")

    def _get_website_company(self):
        return request.website.company_id or request.env.company

    def _get_reservation_timezone(self):
        company = self._get_website_company()
        tz_name = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("restaurant.reservation_website_tz", "")
            .strip()
            or getattr(company, "tz", False)
            or request.website.partner_id.tz
            or self.DEFAULT_WEBSITE_TZ
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone(self.DEFAULT_WEBSITE_TZ)

    def _default_form_values(self):
        now_utc = fields.Datetime.to_datetime(fields.Datetime.now())
        timezone = self._get_reservation_timezone()
        now_local = pytz.UTC.localize(now_utc).astimezone(timezone)
        suggested = now_local + timedelta(hours=1)
        rounded_minute = (suggested.minute // 15) * 15
        suggested = suggested.replace(minute=rounded_minute, second=0, microsecond=0)
        return {
            "customer_name": "",
            "customer_phone": "",
            "customer_email": "",
            "reservation_date": suggested.date().isoformat(),
            "start_time": suggested.strftime("%H:%M"),
            "guest_count": "2",
            "customer_note": "",
        }

    def _render_form(self, error_message=False, form_values=None, status=200):
        values = self._default_form_values()
        if form_values:
            values.update(form_values)
        return request.render(
            "restaurant_table_reservations.website_table_reservation_form",
            {
                "error_message": error_message,
                "form_values": values,
            },
            status=status,
        )

    def _parse_start_datetime_utc(self, reservation_date, start_time):
        try:
            naive_local = datetime.strptime(
                f"{reservation_date} {start_time}", "%Y-%m-%d %H:%M"
            )
        except ValueError as err:
            raise ValidationError(
                "La fecha u hora de la reserva no tiene un formato valido."
            ) from err

        timezone = self._get_reservation_timezone()

        try:
            local_dt = timezone.localize(naive_local, is_dst=None)
        except (AmbiguousTimeError, NonExistentTimeError) as err:
            raise ValidationError(
                "La fecha u hora de la reserva no es valida para la zona horaria."
            ) from err

        utc_dt = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        return utc_dt

    def _select_best_table(self, tables):
        if not tables:
            return False
        return min(
            tables,
            key=lambda table: (
                table.capacity or 0,
                (table.name or "").lower(),
                table.id,
            ),
        )

    def _friendly_error_message(self, exc):
        message = str(exc) if exc else ""
        normalized = message.lower()

        if "fecha" in normalized and "fin" in normalized:
            return "La fecha seleccionada no es valida."
        if "numero de personas" in normalized or "capacidad" in normalized:
            return "La cantidad de personas supera la capacidad disponible."
        if "reserva activa" in normalized or "mesa" in normalized and "horario" in normalized:
            return (
                "No existen mesas disponibles para el horario seleccionado. "
                "Por favor intenta con otra hora o fecha."
            )
        if "mesa inactiva" in normalized:
            return "No hay mesas disponibles para el horario seleccionado."

        return "No se pudo registrar la reserva. Intenta nuevamente."

    @route("/reservas-mesa", type="http", auth="public", website=True, sitemap=True)
    def reservation_form(self, **kwargs):
        return self._render_form(form_values=kwargs)

    @route(
        "/reservas-mesa/enviar",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def reservation_submit(self, **post):
        form_values = {
            "customer_name": (post.get("customer_name") or "").strip(),
            "customer_phone": (post.get("customer_phone") or "").strip(),
            "customer_email": (post.get("customer_email") or "").strip(),
            "reservation_date": (post.get("reservation_date") or "").strip(),
            "start_time": (post.get("start_time") or "").strip(),
            "guest_count": (post.get("guest_count") or "").strip(),
            "customer_note": (post.get("customer_note") or "").strip(),
        }

        if not form_values["customer_name"]:
            return self._render_form(
                "Debes ingresar tu nombre.", form_values=form_values, status=400
            )
        if not form_values["customer_phone"]:
            return self._render_form(
                "Debes ingresar un telefono de contacto.",
                form_values=form_values,
                status=400,
            )
        if not self.PHONE_RE.match(form_values["customer_phone"]):
            return self._render_form(
                "El telefono no es valido.",
                form_values=form_values,
                status=400,
            )
        if not form_values["reservation_date"] or not form_values["start_time"]:
            return self._render_form(
                "Debes seleccionar fecha y hora de la reserva.",
                form_values=form_values,
                status=400,
            )

        customer_email = form_values["customer_email"]
        if customer_email and not self.EMAIL_RE.match(customer_email):
            return self._render_form(
                "El correo electronico no es valido.",
                form_values=form_values,
                status=400,
            )

        try:
            guest_count = int(form_values["guest_count"])
            if guest_count <= 0:
                raise ValueError
        except ValueError:
            return self._render_form(
                "La cantidad de personas debe ser mayor que cero.",
                form_values=form_values,
                status=400,
            )

        try:
            start_datetime = self._parse_start_datetime_utc(
                form_values["reservation_date"], form_values["start_time"]
            )
        except ValidationError as err:
            return self._render_form(
                self._friendly_error_message(err),
                form_values=form_values,
                status=400,
            )

        now_utc = fields.Datetime.to_datetime(fields.Datetime.now())
        if start_datetime <= now_utc:
            return self._render_form(
                "No puedes reservar en un horario pasado.",
                form_values=form_values,
                status=400,
            )

        end_datetime = fields.Datetime.add(
            start_datetime, minutes=self.DEFAULT_RESERVATION_MINUTES
        )

        company = self._get_website_company()
        reservation_model = request.env["restaurant.table.reservation"].sudo()

        try:
            available_tables = reservation_model.get_available_tables(
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                guest_count=guest_count,
                company_id=company.id,
            )
        except (ValidationError, UserError) as err:
            return self._render_form(
                self._friendly_error_message(err),
                form_values=form_values,
                status=400,
            )

        if not available_tables:
            return self._render_form(
                "No existen mesas disponibles para el horario seleccionado. "
                "Por favor intenta con otra hora o fecha.",
                form_values=form_values,
                status=409,
            )

        table = self._select_best_table(available_tables)
        if not reservation_model.is_table_available(
            table.id, start_datetime, end_datetime
        ):
            return self._render_form(
                "No existen mesas disponibles para el horario seleccionado. "
                "Por favor intenta con otra hora o fecha.",
                form_values=form_values,
                status=409,
            )

        user = request.env.user
        partner_id = False if user._is_public() else user.partner_id.id
        responsible_user_id = False
        if not user._is_public() and not user.share:
            responsible_user_id = user.id

        vals = {
            "customer_name": form_values["customer_name"],
            "customer_phone": form_values["customer_phone"],
            "customer_email": customer_email or False,
            "guest_count": guest_count,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "customer_note": form_values["customer_note"] or False,
            "source_channel": "website",
            "source_reference": f"WEB-{uuid4().hex[:10].upper()}",
            "state": "confirmed",
            "table_id": table.id,
            "company_id": company.id,
            "partner_id": partner_id,
            "user_id": responsible_user_id,
        }

        try:
            reservation = reservation_model.create(vals)
        except (ValidationError, UserError) as err:
            return self._render_form(
                self._friendly_error_message(err),
                form_values=form_values,
                status=400,
            )
        except Exception:
            _logger.exception("Error creando reserva web de mesa")
            return self._render_form(
                "No se pudo registrar la reserva. Intenta nuevamente.",
                form_values=form_values,
                status=500,
            )

        timezone = self._get_reservation_timezone()
        local_start = pytz.UTC.localize(
            fields.Datetime.to_datetime(reservation.start_datetime)
        ).astimezone(timezone)

        request.session[self.SESSION_CONFIRM_KEY] = {
            "reference": reservation.name,
            "customer_name": reservation.customer_name,
            "guest_count": reservation.guest_count,
            "table_name": reservation.table_id.display_name
            or f"Mesa #{reservation.table_id.id}",
            "date": local_start.strftime("%Y-%m-%d"),
            "time": local_start.strftime("%H:%M"),
        }
        return request.redirect("/reservas-mesa/confirmacion")

    @route(
        "/reservas-mesa/confirmacion",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def reservation_confirmation(self, **kwargs):
        reservation_info = request.session.get(self.SESSION_CONFIRM_KEY)
        if not reservation_info:
            return request.redirect("/reservas-mesa")

        return request.render(
            "restaurant_table_reservations.website_table_reservation_confirmation",
            {
                "reservation": reservation_info,
            },
        )
