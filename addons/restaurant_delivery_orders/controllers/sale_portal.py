from odoo import http
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortalNoQuotations(CustomerPortal):
    def _prepare_quotations_domain(self, partner):
        return [("id", "=", 0)]

    @http.route(["/my/quotes", "/my/quotes/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_quotes(self, **kwargs):
        return request.redirect("/my/orders")
