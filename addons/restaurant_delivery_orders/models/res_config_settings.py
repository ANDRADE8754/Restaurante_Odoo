from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    delivery_fee_default = fields.Float(
        string="Costo de entrega por defecto",
        config_parameter="restaurant.default_delivery_fee",
        default=1.50,
    )
    delivery_max_concurrent_orders = fields.Integer(
        string="Máx. pedidos simultáneos por repartidor",
        config_parameter="restaurant.delivery_max_concurrent_orders",
        default=5,
    )
    delivery_default_prep_minutes = fields.Integer(
        string="Tiempo base de preparación (min)",
        config_parameter="restaurant.delivery_default_prep_minutes",
        default=20,
    )
    delivery_default_travel_minutes = fields.Integer(
        string="Tiempo base de viaje (min)",
        config_parameter="restaurant.delivery_default_travel_minutes",
        default=25,
    )
    delivery_send_status_emails = fields.Boolean(
        string="Enviar emails de estado al cliente",
        config_parameter="restaurant.delivery_send_status_emails",
        default=True,
    )
    delivery_claim_hours_limit = fields.Integer(
        string="Horas limite para reclamos",
        config_parameter="restaurant.delivery_claim_hours_limit",
        default=48,
    )
