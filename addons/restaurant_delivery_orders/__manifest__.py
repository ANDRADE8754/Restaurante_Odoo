{
    'name': 'Pedidos a Domicilio Casa Vieja',
    'version': '1.0.0',
    'category': 'Restaurant/Delivery',
    'summary': 'Gestión de pedidos a domicilio para Restaurante Casa Vieja',
    'description': """
Pedidos a Domicilio Casa Vieja
==============================

Módulo desarrollado por ARCM Solutions. Gestiona la operación de pedidos
a domicilio del Restaurante Casa Vieja: registro de cliente, líneas de
producto, estados del pedido y enlaces a POS / facturación.
""",
    'author': 'ARCM Solutions',
    'website': 'https://www.arcmsolutions.local',
    'license': 'LGPL-3',

    'depends': [
        'restaurant_casa_vieja_base',
        'base',
        'mail',
        'contacts',
        'product',
        'point_of_sale',
        'account',
        'website',
        'website_sale',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'data/config_data.xml',
        'data/delivery_schedule_data.xml',
        'data/mail_templates.xml',
        'data/sequence_data.xml',
        'data/website_menu.xml',
        'views/sale_portal_templates.xml',
        'views/delivery_rating_templates.xml',
        'views/delivery_claim_portal_templates.xml',
        'views/website_sale_checkout_templates.xml',
        'views/delivery_zone_views.xml',
        'views/delivery_schedule_views.xml',
        'views/res_config_settings_views.xml',
        'views/delivery_order_views.xml',
        'views/delivery_claim_views.xml',
        'views/product_rating_views.xml',
        'views/delivery_driver_dashboard.xml',
        'wizard/delivery_cancel_wizard_view.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
