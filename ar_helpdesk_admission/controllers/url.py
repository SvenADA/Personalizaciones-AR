from odoo import http
from odoo.http import request

class ServiceRequest(http.Controller):

    @http.route('/request', type='http', auth="public", csrf=False, website=True)
    def service_request(self, **kw):
        return http.request.render("ar_helpdesk_admission.request_form", {})

    @http.route('/create/request', type='http', auth="public", csrf=False, website=True)
    def create_request(self, **kw):
        request.env['solicitud_admision'].sudo().create(kw)
        return http.request.render("ar_helpdesk_admission.request_received", {})
