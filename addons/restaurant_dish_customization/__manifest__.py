{
    'name': 'Personalización de Platos Casa Vieja',
    'version': '1.0.0',
    'category': 'Restaurant/Customization',
    'summary': 'Personalización de platos para Restaurante Casa Vieja (estructura inicial)',
    'description': """
Personalización de Platos Casa Vieja
====================================

Estructura base del módulo de personalización de platos. ARCM Solutions.
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
        'product',
        'point_of_sale',
        'crm',
        'website',
    ],

    'data': [
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
