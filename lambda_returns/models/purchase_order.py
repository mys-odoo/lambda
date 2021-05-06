# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_returned = fields.Float(string="Returned", digits='Product Unit of Measure', compute='_compute_qty_returned')
    qty_total_received = fields.Float(string="Total Recieved",
                                      digits='Product Unit of Measure',
                                      compute='_compute_qty_total_received')

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_returned(self):
        for line in self:
            qty = 0.0
            for move in line.move_ids.filtered(lambda m: m.product_id == line.product_id and m.state not in ['cancel']):
                if move.to_refund:
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
            line.qty_returned = qty

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_total_received(self):
        kit_lines = self.env['purchase.order.line']
        for line in self:
            if line.qty_received_method == 'stock_moves' and line.move_ids:
                kit_bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=line.company_id.id,
                                                        bom_type='phantom')
                if kit_bom:
                    moves = line.move_ids.filtered(lambda m: m.state == 'done' and not m.scrapped)
                    order_qty = line.product_uom._compute_quantity(line.product_uom_qty, kit_bom.product_uom_id)
                    filters = {
                        'incoming_moves': lambda m: m.location_id.usage == 'supplier' and (
                                    not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m: m.location_id.usage != 'supplier' and m.to_refund
                    }
                    line.qty_total_received = moves._compute_kit_quantities(line.product_id, order_qty, kit_bom, filters)
                    kit_lines += line

        self = self - kit_lines
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_total_received = line.qty_received_manual or 0.0
            else:
                line.qty_total_received = 0.0

        for line in self:
            if line.qty_received_method == 'stock_moves':
                total = 0.0
                # In case of a BOM in kit, the products delivered do not correspond to the products in
                # the PO. Therefore, we can skip them since they will be handled later on.
                for move in line.move_ids.filtered(lambda m: m.product_id == line.product_id):
                    if move.state == 'done':
                        if move.location_dest_id.usage == "supplier":
                            if move.to_refund:
                                # total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                                pass
                        elif move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned():
                            # Edge case: the dropship is returned to the stock, no to the supplier.
                            # In this case, the received quantity on the PO is set although we didn't
                            # receive the product physically in our stock. To avoid counting the
                            # quantity twice, we do nothing.
                            pass
                        elif (
                            move.location_dest_id.usage == "internal"
                            and move.to_refund
                            and move.location_dest_id
                            not in self.env["stock.location"].search(
                                [("id", "child_of", move.warehouse_id.view_location_id.id)]
                            )
                        ):
                            # total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                            pass
                        else:
                            total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                line.qty_total_received = total