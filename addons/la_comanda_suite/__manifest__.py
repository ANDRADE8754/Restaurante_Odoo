{
    'name': 'Gestión de Restaurante La Comanda - Suite Completa',
    'version': '1.0',
    'category': 'Restaurant',
    'summary': 'Suite completa de gestión de restaurante La Comanda',
    'description': 'Módulo contenedor que instala automáticamente todos los módulos del sistema de gestión de La Comanda: Pedidos, Reservas e Inventario.',
    'author': 'Alejandro Andrade, Kevin Carrasco, Marco Serrano, Jonathan Lozada, Juan López, Elvis Flores',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'restaurant_orders',
        'table_reservations',
        'restaurant_inventory',
        'l10n_ec',
    ],
    'data': [
        'data/menu_data.xml',
        'data/products_data.xml',
        'data/ingredients_products.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
