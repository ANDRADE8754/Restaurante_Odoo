from odoo import models, fields, api

class IngredientCategory(models.Model):
    _name = 'ingredient.category'
    _description = 'Categoría de Ingrediente'
    _rec_name = 'name'

    name = fields.Char('Nombre', required=True)
    description = fields.Text('Descripción')
    active = fields.Boolean('Activa', default=True)


class Ingredient(models.Model):
    _name = 'restaurant.ingredient'
    _description = 'Ingrediente de Restaurante'
    _rec_name = 'name'

    # Información básica
    name = fields.Char('Nombre del Ingrediente', required=True)
    category_id = fields.Many2one('ingredient.category', string='Categoría', required=True, ondelete='restrict')
    description = fields.Text('Descripción')
    
    # Stock
    quantity_on_hand = fields.Float('Cantidad en Stock', default=0)
    unit_of_measure = fields.Selection([
        ('kg', 'Kilogramos (kg)'),
        ('g', 'Gramos (g)'),
        ('l', 'Litros (l)'),
        ('ml', 'Mililitros (ml)'),
        ('unit', 'Unidades'),
        ('dozen', 'Docenas'),
    ], string='Unidad de Medida', required=True, default='kg')
    
    # Precios
    unit_cost = fields.Float('Costo Unitario (USD)', required=True)
    
    # Control de stock
    minimum_quantity = fields.Float('Cantidad Mínima para Reorden', required=True, default=10)
    maximum_quantity = fields.Float('Cantidad Máxima de Stock', required=True, default=100)
    reorder_quantity = fields.Float('Cantidad de Reorden', required=True, default=50)
    
    # Proveedor
    supplier_id = fields.Many2one('res.partner', string='Proveedor Preferido', domain=[('supplier_rank', '>', 0)])
    lead_time_days = fields.Integer('Tiempo de Entrega (días)', default=3)
    
    # Estado
    STATE_SELECTION = [
        ('ok', 'Stock Normal'),
        ('low', 'Stock Bajo'),
        ('critical', 'Stock Crítico'),
    ]
    stock_state = fields.Selection(STATE_SELECTION, string='Estado de Stock', compute='_compute_stock_state', store=True)
    
    # Información adicional
    expiration_control = fields.Boolean('Requiere Control de Expiración')
    allergen_info = fields.Text('Información de Alérgenos')
    active = fields.Boolean('Activo', default=True)
    
    # Auditoría
    last_stock_check = fields.Datetime('Último Conteo de Stock')
    
    @api.depends('quantity_on_hand')
    def _compute_stock_state(self):
        """Calcular estado de stock basado en cantidad mínima"""
        for ingredient in self:
            if ingredient.quantity_on_hand <= 0:
                ingredient.stock_state = 'critical'
            elif ingredient.quantity_on_hand <= ingredient.minimum_quantity:
                ingredient.stock_state = 'low'
            else:
                ingredient.stock_state = 'ok'
    
    def action_reorder(self):
        """Crear una orden de compra para reabastecer"""
        # Crear orden de compra
        purchase_line_vals = {
            'product_id': self.id,
            'product_qty': self.reorder_quantity,
            'price_unit': self.unit_cost,
        }
        # Implementación real incluiría creación de purchase.order


class StockMovement(models.Model):
    _name = 'restaurant.stock.movement'
    _description = 'Movimiento de Inventario'
    _rec_name = 'name'

    name = fields.Char('Descripción del Movimiento')
    ingredient_id = fields.Many2one('restaurant.ingredient', string='Ingrediente', required=True, ondelete='cascade')
    
    MOVEMENT_TYPE = [
        ('in', 'Entrada'),
        ('out', 'Salida'),
        ('adjustment', 'Ajuste'),
    ]
    movement_type = fields.Selection(MOVEMENT_TYPE, string='Tipo de Movimiento', required=True)
    
    quantity = fields.Float('Cantidad', required=True)
    reason = fields.Char('Motivo (ej: Compra, Uso, Daño)')
    
    movement_date = fields.Datetime('Fecha del Movimiento', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='Registrado por', default=lambda self: self.env.user, readonly=True)
    
    notes = fields.Text('Notas')
