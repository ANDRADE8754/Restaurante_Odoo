from odoo import api, fields, models


class DeliveryZone(models.Model):
    _name = "restaurant.delivery.zone"
    _description = "Zona de cobertura delivery"
    _order = "name"

    name = fields.Char(string="Nombre de zona", required=True)
    code = fields.Char(string="Código", size=10)
    active = fields.Boolean(default=True)
    delivery_fee = fields.Float(
        string="Costo de envío",
        required=True,
        digits=(10, 2),
    )
    estimated_minutes = fields.Integer(
        string="Tiempo estimado (min)",
        default=30,
    )
    sector_ids = fields.One2many(
        comodel_name="restaurant.delivery.sector",
        inverse_name="zone_id",
        string="Sectores",
    )
    notes = fields.Text(string="Notas internas")
    color = fields.Integer(string="Color")
    order_count = fields.Integer(
        string="Pedidos",
        compute="_compute_order_count",
    )

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Ya existe una zona con este nombre."),
    ]

    @api.depends("name")
    def _compute_order_count(self):
        order_model = self.env["restaurant.delivery.order"]
        for zone in self:
            zone.order_count = order_model.search_count([("delivery_zone_id", "=", zone.id)])
