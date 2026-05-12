{
    'name': 'Reservas de Mesa Casa Vieja',
    'version': '1.0.0',
    'category': 'Restaurant/Reservations',
    'summary': 'Gestión de reservas de mesa para Restaurante Casa Vieja (estructura inicial)',
    'description': """
Reservas de Mesa Casa Vieja
===========================

Estructura base del módulo de reservas de mesa. ARCM Solutions.
La implementación de modelos, vistas y reglas se realizará en una fase posterior.
""",
    'author': 'ARCM Solutions',
    'website': 'https://www.arcmsolutions.local',
    'license': 'LGPL-3',

    'depends': [
        'restaurant_casa_vieja_base',
        'base',
        'mail',
        'contacts',
        'crm',
        'point_of_sale',
        'website',
    ],

    'data': [
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
