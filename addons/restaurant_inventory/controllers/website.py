from odoo import http
from odoo.http import request

class InventoryController(http.Controller):
    
    @http.route('/restaurant/inventory/categories', auth='public', website=True)
    def list_categories(self, **kwargs):
        """Listar categorías de ingredientes"""
        categories = request.env['ingredient.category'].sudo().search([])
        return request.render('restaurant_inventory.inventory_categories_template', {
            'categories': categories,
        })
    
    @http.route('/restaurant/inventory/category/<int:category_id>', auth='public', website=True)
    def view_category(self, category_id, **kwargs):
        """Ver ingredientes de una categoría"""
        category = request.env['ingredient.category'].sudo().browse(category_id)
        ingredients = request.env['restaurant.ingredient'].sudo().search([('category_id', '=', category_id)])
        return request.render('restaurant_inventory.inventory_category_detail_template', {
            'category': category,
            'ingredients': ingredients,
        })
    
    @http.route('/restaurant/inventory/ingredient/<int:ingredient_id>', auth='public', website=True)
    def view_ingredient(self, ingredient_id, **kwargs):
        """Ver detalles del ingrediente"""
        ingredient = request.env['restaurant.ingredient'].sudo().browse(ingredient_id)
        return request.render('restaurant_inventory.ingredient_detail_template', {
            'ingredient': ingredient,
        })
    
    @http.route('/restaurant/inventory/status', auth='public', website=True)
    def inventory_status(self, **kwargs):
        """Ver estado general del inventario"""
        ingredients = request.env['restaurant.ingredient'].sudo().search([])
        critical = request.env['restaurant.ingredient'].sudo().search([('stock_state', '=', 'critical')])
        low = request.env['restaurant.ingredient'].sudo().search([('stock_state', '=', 'low')])
        ok = request.env['restaurant.ingredient'].sudo().search([('stock_state', '=', 'ok')])
        
        return request.render('restaurant_inventory.inventory_status_template', {
            'ingredients': ingredients,
            'critical': critical,
            'low': low,
            'ok': ok,
        })
