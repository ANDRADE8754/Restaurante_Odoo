{
    'name': 'Gestión de Restaurante La Comanda',
    'version': '1.0',
    'category': 'Restaurant',
    'summary': 'Módulo para pedidos a domicilio y reservas',
    'author': 'Alejandro Andrade, Kevin Carrasco, Marco Serrano, Jonathan Lozada, Juan López, Elvis Flores',
    'depends': [
        'base',
        'website', 
        'pos_restaurant', 
        'stock', 
        'purchase', 
        'account', 
        'crm',
        'l10n_ec'
    ],
    'data': [
        'data/master_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}