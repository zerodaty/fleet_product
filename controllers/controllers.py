# -*- coding: utf-8 -*-
# from odoo import http


# class FleetProduct(http.Controller):
#     @http.route('/fleet_product/fleet_product', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fleet_product/fleet_product/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('fleet_product.listing', {
#             'root': '/fleet_product/fleet_product',
#             'objects': http.request.env['fleet_product.fleet_product'].search([]),
#         })

#     @http.route('/fleet_product/fleet_product/objects/<model("fleet_product.fleet_product"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fleet_product.object', {
#             'object': obj
#         })

