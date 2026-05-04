from odoo import http
from odoo.http import request

class RestaurantOrderController(http.Controller):
    
    @http.route('/restaurant/order/create', auth='user', website=True)
    def create_order(self, **kwargs):
        """Crear nuevo pedido desde el sitio web"""
        if request.httprequest.method == 'POST':
            order = request.env['restaurant.order'].sudo().create({
                'partner_id': request.env.user.partner_id.id,
                'delivery_address': kwargs.get('delivery_address', ''),
                'delivery_city': kwargs.get('delivery_city', 'Patate'),
                'estimated_delivery_time': int(kwargs.get('estimated_delivery_time', 45)),
                'delivery_notes': kwargs.get('delivery_notes', ''),
            })
            return request.redirect(f'/restaurant/order/{order.id}')
        
        return request.render('restaurant_orders.order_form_template', {})
    
    @http.route('/restaurant/order/<int:order_id>', auth='user', website=True)
    def view_order(self, order_id, **kwargs):
        """Ver estado del pedido"""
        order = request.env['restaurant.order'].sudo().browse(order_id)
        return request.render('restaurant_orders.order_detail_template', {
            'order': order,
        })
    
    @http.route('/restaurant/orders', auth='user', website=True)
    def list_orders(self, **kwargs):
        """Listar pedidos del usuario actual"""
        partner = request.env.user.partner_id
        orders = request.env['restaurant.order'].sudo().search([('partner_id', '=', partner.id)])
        return request.render('restaurant_orders.orders_list_template', {
            'orders': orders,
        })
