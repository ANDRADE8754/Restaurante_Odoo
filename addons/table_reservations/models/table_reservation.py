from odoo import models, fields, api
from datetime import datetime, timedelta

class TableReservation(models.Model):
    _name = 'table.reservation'
    _description = 'Reserva de Mesa'
    _rec_name = 'reservation_number'

    reservation_number = fields.Char('Número de Reserva', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('table.reservation'))
    
    # Cliente
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, ondelete='restrict')
    phone = fields.Char(related='partner_id.phone', string='Teléfono', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    
    # Mesa
    table_id = fields.Many2one('restaurant.table', string='Mesa', required=True, ondelete='restrict')
    number_of_guests = fields.Integer('Número de Comensales', required=True, default=2)
    
    # Fechas
    reservation_datetime = fields.Datetime('Fecha y Hora de Reserva', required=True)
    estimated_duration = fields.Integer('Duración Estimada (minutos)', default=120)
    
    # Ocasión
    OCCASION_SELECTION = [
        ('normal', 'Normal'),
        ('birthday', 'Cumpleaños'),
        ('anniversary', 'Aniversario'),
        ('business', 'Negocio'),
        ('celebration', 'Celebración'),
        ('romantic', 'Romántica'),
        ('other', 'Otro'),
    ]
    occasion = fields.Selection(OCCASION_SELECTION, string='Ocasión', default='normal')
    
    # Estado
    STATE_SELECTION = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('in_progress', 'En Curso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('no_show', 'No Se Presentó'),
    ]
    state = fields.Selection(STATE_SELECTION, string='Estado', default='pending', required=True, tracking=True)
    
    # Notas
    observations = fields.Text('Observaciones')
    special_requests = fields.Text('Solicitudes Especiales')
    
    # Control
    created_date = fields.Datetime(readonly=True)
    confirmed_date = fields.Datetime(readonly=True)
    
    # Métodos de workflow
    def action_confirm(self):
        """Confirmar reserva"""
        self.write({'state': 'confirmed', 'confirmed_date': fields.Datetime.now()})
        return True
    
    def action_start(self):
        """Iniciar/comenzar la reserva"""
        self.write({'state': 'in_progress'})
        return True
    
    def action_complete(self):
        """Completar la reserva"""
        self.write({'state': 'completed'})
        return True
    
    def action_cancel(self):
        """Cancelar la reserva"""
        self.write({'state': 'cancelled'})
        return True
    
    def action_no_show(self):
        """Marcar como no se presentó"""
        self.write({'state': 'no_show'})
        return True
