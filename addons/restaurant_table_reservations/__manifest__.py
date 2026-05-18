{
    "name": "Reservas de Mesa Casa Vieja",
    "version": "1.0.0",
    "category": "Restaurant/Reservations",
    "summary": "Gestion de reservas de mesa para Restaurante Casa Vieja",
    "description": """
Reservas de Mesa Casa Vieja
===========================

Modulo desarrollado por ARCM Solutions. Gestiona reservas de mesa del
Restaurante Casa Vieja: mesas fisicas, estados de la reserva, validacion de
solapamiento y campos preparados para integracion con Website y POS.
""",
    "author": "ARCM Solutions",
    "website": "https://www.arcmsolutions.local",
    "license": "LGPL-3",
    "depends": [
        "restaurant_casa_vieja_base",
        "base",
        "mail",
        "contacts",
        "point_of_sale",
        "pos_restaurant",
        "website",
    ],
    "data": [
        "security/reservation_security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/restaurant_table_views.xml",
        "views/table_reservation_views.xml",
        "views/table_reservation_pos_views.xml",
        "views/pos_order_views.xml",
        "views/menu_views.xml",
        "views/website_reservation_templates.xml",
        "views/website_menu_views.xml",
    ],
    "demo": [
        "data/demo_tables.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
