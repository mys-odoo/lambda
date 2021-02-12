# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    weight = fields.Float(related="product_id.weight", string="Weight", readonly=False)
    volume = fields.Float(related="product_id.volume", string="Volume", readonly=False)