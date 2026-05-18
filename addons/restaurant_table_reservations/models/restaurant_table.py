from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RestaurantTable(models.Model):
    _inherit = "restaurant.table"
    _description = "Mesa del Restaurante"
    _order = "location_area, name"

    name = fields.Char(
        string="Nombre",
        index=True,
    )
    code = fields.Char(string="Codigo interno")
    capacity = fields.Integer(
        string="Capacidad",
        required=True,
        default=2,
    )
    location_area = fields.Selection(
        selection=[
            ("interior", "Interior"),
            ("terraza", "Terraza"),
            ("jardin", "Jardin"),
            ("salon", "Salon principal"),
            ("otro", "Otro"),
        ],
        string="Zona",
        default="interior",
        required=True,
    )
    floor_id = fields.Many2one(
        comodel_name="restaurant.floor",
        string="Piso POS",
        copy=False,
        index=True,
        help="Compatibilidad con POS Restaurante cuando ese modulo esta instalado.",
    )
    active = fields.Boolean(string="Activa", default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compania",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    notes = fields.Text(string="Notas")

    reservation_ids = fields.One2many(
        comodel_name="restaurant.table.reservation",
        inverse_name="table_id",
        string="Reservas",
    )
    current_reservation_count = fields.Integer(
        string="Reservas activas",
        compute="_compute_current_reservation_count",
    )

    @api.constrains("capacity")
    def _check_capacity_positive(self):
        for table in self:
            if table.capacity <= 0:
                raise ValidationError(_("La capacidad de la mesa debe ser mayor que cero."))

    @api.depends("reservation_ids", "reservation_ids.state")
    def _compute_current_reservation_count(self):
        active_states = ("draft", "confirmed", "seated")
        for table in self:
            table.current_reservation_count = len(
                table.reservation_ids.filtered(lambda r: r.state in active_states)
            )

    @api.depends("name", "code", "capacity", "table_number", "floor_id", "floor_id.name")
    def _compute_display_name(self):
        for table in self:
            if table.name:
                label = table.name
                if table.code:
                    label = "[%s] %s" % (table.code, table.name)
                if table.capacity:
                    label = "%s (cap. %d)" % (label, table.capacity)
                table.display_name = label
                continue
            floor_name = table.floor_id.name if table.floor_id else False
            if floor_name and table.table_number:
                table.display_name = "%s, %s" % (floor_name, table.table_number)
            elif table.table_number:
                table.display_name = _("Mesa %s") % table.table_number
            elif floor_name:
                table.display_name = floor_name
            else:
                table.display_name = _("Mesa sin nombre")
