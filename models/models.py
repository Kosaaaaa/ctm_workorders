# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class ctm_workorders(models.Model):
#     _name = 'ctm_workorders.ctm_workorders'
#     _description = 'ctm_workorders.ctm_workorders'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
