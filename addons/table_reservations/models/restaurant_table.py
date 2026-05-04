from odoo import models, fields, api

class RestaurantTable(models.Model):
    _name = 'restaurant.table'
    _description = 'Mesa de Restaurante'
    _rec_name = 'table_number'

    table_number = fields.Char('Número de Mesa', required=True, unique=True)
    capacity = fields.Integer('Capacidad (comensales)', required=True, default=4)
    location = fields.Char('Ubicación (ej: piso 1, esquina)')
    
    # Estado
    STATE_SELECTION = [
        ('available', 'Disponible'),
        ('reserved', 'Reservada'),
        ('occupied', 'Ocupada'),
        ('maintenance', 'Mantenimiento'),
    ]
    state = fields.Selection(STATE_SELECTION, string='Estado', default='available')
    
    # Descripción
    description = fields.Text('Descripción/Características')
    active = fields.Boolean('Activa', default=True)
    
    # Reservas futuras
    reservation_ids = fields.One2many('table.reservation', 'table_id', string='Reservas')


class TableReservation(models.Model):
    _name = 'table.reservation'
    _description = 'Reserva de Mesa'
    _rec_name = 'reservation_number'

    reservation_number = fields.Char('Número de Reserva', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('table.reservation'))
    
    # Cliente
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, ondelete='restrict')
    phone = fields.Char(related='partner_id.phone', string='Teléfono', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    
    # Mesa y comensales
    table_id = fields.Many2one('restaurant.table', string='Mesa', required=True, ondelete='restrict')
    number_of_guests = fields.Integer('Número de Comensales', required=True)
    
    # Fecha y hora
    reservation_datetime = fields.Datetime('Fecha y Hora de Reserva', required=True)
    estimated_duration = fields.Integer('Duración Estimada (minutos)', default=120)
    
    # Ocasión
    OCCASION_SELECTION = [
        ('normal', 'Reunión Normal'),
        ('birthday', 'Cumpleaños'),
        ('anniversary', 'Aniversario'),
        ('business', 'Reunión de Negocios'),
        ('celebration', 'Celebración'),
        ('romantic', 'Cena Romántica'),
        ('other', 'Otra Ocasión'),
    ]
    occasion = fields.Selection(OCCASION_SELECTION, string='Ocasión Especial', default='normal')
    
    # Estado
    STATE_SELECTION = [
        ('pending', 'Pendiente de Confirmación'),
        ('confirmed', 'Confirmada'),
        ('in_progress', 'En Curso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('no_show', 'No se Presentó'),
    ]
    state = fields.Selection(STATE_SELECTION, string='Estado', default='pending', tracking=True)
    
    # Notas
    observations = fields.Text('Observaciones')
    special_requests = fields.Text('Solicitudes Especiales (ej: decoración, música, etc.)')
    
    # Control
    created_date = fields.Datetime('Creada el', default=fields.Datetime.now, readonly=True)
    confirmed_date = fields.Datetime('Confirmada el', readonly=True)
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Cargar datos del cliente"""
        if self.partner_id:
            self.phone = self.partner_id.phone
            self.email = self.partner_id.email
    
    @api.onchange('number_of_guests', 'table_id')
    def _onchange_guests_table(self):
        """Validar que la mesa tenga suficiente capacidad"""
        if self.table_id and self.number_of_guests:
            if self.number_of_guests > self.table_id.capacity:
                return {
                    'warning': {
                        'title': 'Capacidad Insuficiente',
                        'message': f'La mesa solo tiene capacidad para {self.table_id.capacity} comensales. Se necesita una mesa más grande.'
                    }
                }
