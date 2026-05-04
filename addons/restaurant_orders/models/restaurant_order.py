from odoo import models, fields, api
from datetime import datetime, timedelta

class RestaurantOrder(models.Model):
    _name = 'restaurant.order'
    _description = 'Pedido a Domicilio'
    _rec_name = 'order_number'

    order_number = fields.Char('Número de Pedido', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('restaurant.order'))
    
    # Cliente
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, ondelete='restrict')
    phone = fields.Char(related='partner_id.phone', string='Teléfono', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    
    # Dirección de entrega
    delivery_address = fields.Text('Dirección de Entrega', required=True)
    delivery_city = fields.Char('Ciudad')
    delivery_notes = fields.Text('Notas de Entrega')
    
    # Productos
    order_line_ids = fields.One2many('restaurant.order.line', 'order_id', string='Líneas de Pedido')
    
    # Tiempos
    order_date = fields.Datetime('Fecha del Pedido', default=fields.Datetime.now, required=True)
    estimated_delivery_time = fields.Integer('Tiempo Estimado (minutos)', default=45)
    delivery_date = fields.Datetime('Fecha de Entrega Estimada', compute='_compute_delivery_date')
    
    # Repartidor
    delivery_person_id = fields.Many2one('res.partner', string='Repartidor Asignado', domain=[('is_delivery_person', '=', True)])
    
    # Estado
    STATE_SELECTION = [
        ('pending', 'Pendiente'),
        ('preparing', 'En Preparación'),
        ('ready', 'Listo'),
        ('on_way', 'En Camino'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ]
    state = fields.Selection(STATE_SELECTION, string='Estado', default='pending', required=True, tracking=True)
    
    # Dinero
    total_amount = fields.Float('Total', compute='_compute_total', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Control
    create_date = fields.Datetime(readonly=True)
    write_date = fields.Datetime(readonly=True)
    
    @api.depends('order_line_ids.price_subtotal')
    def _compute_total(self):
        for order in self:
            order.total_amount = sum(line.price_subtotal for line in order.order_line_ids)
    
    @api.depends('order_date', 'estimated_delivery_time')
    def _compute_delivery_date(self):
        for order in self:
            if order.order_date:
                order.delivery_date = order.order_date + timedelta(minutes=order.estimated_delivery_time)
            else:
                order.delivery_date = False
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Cargar datos del cliente"""
        if self.partner_id:
            self.delivery_city = self.partner_id.city or 'Patate'
    
    # Métodos de workflow
    def action_confirm(self):
        """Confirmar pedido"""
        self.write({'state': 'preparing'})
        return True
    
    def action_preparing(self):
        """Marcar como en preparación"""
        self.write({'state': 'preparing'})
        return True
    
    def action_ready(self):
        """Marcar como listo"""
        self.write({'state': 'ready'})
        return True
    
    def action_on_way(self):
        """Marcar como en camino"""
        self.write({'state': 'on_way'})
        return True
    
    def action_delivered(self):
        """Marcar como entregado"""
        self.write({'state': 'delivered'})
        return True
    
    def action_cancel(self):
        """Cancelar pedido"""
        self.write({'state': 'cancelled'})
        return True


class RestaurantOrderLine(models.Model):
    _name = 'restaurant.order.line'
    _description = 'Línea de Pedido a Domicilio'

    order_id = fields.Many2one('restaurant.order', string='Pedido', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True, ondelete='restrict')
    quantity = fields.Integer('Cantidad', default=1, required=True)
    unit_price = fields.Float('Precio Unitario', related='product_id.list_price')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True)
    
    notes = fields.Char('Observaciones (ej: picante, sin cebolla)')
    
    @api.depends('quantity', 'unit_price')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.unit_price
