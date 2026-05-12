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
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/delivery_order_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
