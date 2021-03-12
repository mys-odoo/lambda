# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_returned = fields.Float(string="Returned", digits='Product Unit of Measure', compute='_compute_qty_returned')

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_returned(self):
        for line in self:
            qty = 0.0
            for move in line.move_ids.filtered(lambda m: m.product_id == line.product_id and m.state not in ['cancel']):
                if move.to_refund:
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
            line.qty_returned = qty
