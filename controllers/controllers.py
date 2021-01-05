# -*- coding: utf-8 -*-
# from odoo import http


# class CtmWorkorders(http.Controller):
#     @http.route('/ctm_workorders/ctm_workorders/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ctm_workorders/ctm_workorders/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ctm_workorders.listing', {
#             'root': '/ctm_workorders/ctm_workorders',
#             'objects': http.request.env['ctm_workorders.ctm_workorders'].search([]),
#         })

#     @http.route('/ctm_workorders/ctm_workorders/objects/<model("ctm_workorders.ctm_workorders"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ctm_workorders.object', {
#             'object': obj
#         })
