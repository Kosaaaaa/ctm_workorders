# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    is_independent = fields.Boolean(default=False)

