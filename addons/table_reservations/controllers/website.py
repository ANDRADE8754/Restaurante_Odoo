from odoo import http
from odoo.http import request

class TableReservationController(http.Controller):
    
    @http.route('/restaurant/reservation/create', auth='user', website=True)
    def create_reservation(self, **kwargs):
        """Crear nueva reserva desde el sitio web"""
        tables = request.env['restaurant.table'].sudo().search([('state', '=', 'available')])
        
        if request.httprequest.method == 'POST':
            reservation = request.env['table.reservation'].sudo().create({
                'partner_id': request.env.user.partner_id.id,
                'table_id': int(kwargs.get('table_id', 0)),
                'number_of_guests': int(kwargs.get('number_of_guests', 2)),
                'reservation_datetime': kwargs.get('reservation_datetime', ''),
                'estimated_duration': int(kwargs.get('estimated_duration', 120)),
                'occasion': kwargs.get('occasion', 'normal'),
                'special_requests': kwargs.get('special_requests', ''),
            })
            return request.redirect(f'/restaurant/reservation/{reservation.id}')
        
        return request.render('table_reservations.reservation_form_template', {
            'tables': tables,
        })
    
    @http.route('/restaurant/reservation/<int:reservation_id>', auth='user', website=True)
    def view_reservation(self, reservation_id, **kwargs):
        """Ver detalles de la reserva"""
        reservation = request.env['table.reservation'].sudo().browse(reservation_id)
        return request.render('table_reservations.reservation_detail_template', {
            'reservation': reservation,
        })
    
    @http.route('/restaurant/reservations', auth='user', website=True)
    def list_reservations(self, **kwargs):
        """Listar reservas del usuario actual"""
        partner = request.env.user.partner_id
        reservations = request.env['table.reservation'].sudo().search([('partner_id', '=', partner.id)])
        return request.render('table_reservations.reservations_list_template', {
            'reservations': reservations,
        })
    
    @http.route('/restaurant/tables/available', auth='public', website=True)
    def available_tables(self, **kwargs):
        """Ver mesas disponibles (sin autenticación)"""
        tables = request.env['restaurant.table'].sudo().search([('state', '=', 'available')])
        return request.render('table_reservations.available_tables_template', {
            'tables': tables,
        })
