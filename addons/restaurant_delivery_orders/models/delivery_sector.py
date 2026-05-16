from odoo import fields, models


class DeliverySector(models.Model):
    _name = "restaurant.delivery.sector"
    _description = "Sector dentro de zona delivery"

    name = fields.Char(string="Sector/Barrio", required=True)
    zone_id = fields.Many2one(
        comodel_name="restaurant.delivery.zone",
        string="Zona",
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "name_zone_uniq",
            "unique(name, zone_id)",
            "Este sector ya existe en la zona.",
        ),
    ]
