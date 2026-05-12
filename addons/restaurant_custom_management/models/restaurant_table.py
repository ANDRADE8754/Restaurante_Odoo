from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RestaurantTable(models.Model):
    _name = "restaurant.table"
    _description = "Mesa de Restaurante"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "location, name"

    name = fields.Char(string="Mesa", required=True, tracking=True)
    code = fields.Char(string="Código corto")
    capacity = fields.Integer(string="Capacidad", required=True, default=4)
    location = fields.Selection(
        selection=[
            ("main_hall", "Salón principal"),
            ("terrace", "Terraza"),
            ("private_room", "Área privada"),
            ("outdoor", "Exterior"),
        ],
        string="Ubicación",
    )
    state = fields.Selection(
        selection=[
            ("available", "Disponible"),
            ("occupied", "Ocupada"),
            ("maintenance", "Mantenimiento"),
        ],
        string="Estado",
        default="available",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(string="Activa", default=True)
    notes = fields.Text(string="Observaciones internas")
    reservation_ids = fields.One2many(
        comodel_name="restaurant.table.reservation",
        inverse_name="table_id",
        string="Reservas",
    )
    reservation_count = fields.Integer(
        string="Reservas",
        compute="_compute_reservation_count",
    )

    @api.depends("reservation_ids")
    def _compute_reservation_count(self):
        grouped_reservations = self.env["restaurant.table.reservation"].read_group(
            domain=[("table_id", "in", self.ids)],
            fields=["table_id"],
            groupby=["table_id"],
        )
        reservation_count_by_table = {
            group["table_id"][0]: group["table_id_count"]
            for group in grouped_reservations
        }
        for table in self:
            table.reservation_count = reservation_count_by_table.get(table.id, 0)

    @api.constrains("capacity")
    def _check_capacity(self):
        for table in self:
            if table.capacity <= 0:
                raise ValidationError(_("La capacidad de la mesa debe ser mayor que cero."))

    def action_view_reservations(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "restaurant_custom_management.action_restaurant_table_reservation"
        )
        action["domain"] = [("table_id", "=", self.id)]
        action["context"] = {
            "default_table_id": self.id,
            "search_default_table_id": self.id,
        }
        return action
