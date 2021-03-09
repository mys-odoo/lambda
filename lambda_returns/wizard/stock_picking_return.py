# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):

        picking_id, picking_type_id = super(ReturnPicking, self)._create_returns()
        print("Hello")

        for test in self.product_return_moves:
            print("checking")

        # Get the return picking (Transfer Receipt)
        pick = self.env['stock.picking'].browse(picking_id)

        inv_ids = pick.purchase_id.invoice_ids.filtered(lambda i: i.state == 'posted')

        # Only look at the invoices that are related
        for inv in pick.purchase_id.invoice_ids.filtered(lambda i: i.state == 'posted'):
            # Create the credit note if inv matches the move POL
            # If the PO id matches in the stock moves and in the invoice lines of the related Bill(inv)
            sml = pick.move_line_ids_without_package.filtered(lambda ml: ml.move_id.purchase_line_id in inv.invoice_line_ids.purchase_line_id)
            if sml:
                reversal = self.env['account.move.reversal'].create({
                    'move_ids': [(4, inv.id, 0)],
                    'refund_method': 'refund',
                })
                res = reversal.reverse_moves()
                credit_note = self.env['account.move'].search([('reversed_entry_id', '=', inv.id)],
                                                              order='create_date desc', limit=1)
                # TODO: check what this does from EHE's old code from aryse
                # credit_note.sudo().update_with_picking(self)

                for inv_line in credit_note.invoice_line_ids:
                    print("i'm at this line")
                    move_line = sml.filtered(lambda ml: ml.product_id == inv_line.product_id)
                    if move_line:
                        update_qty = move_line.product_uom_qty
                    else:
                        update_qty = 0.0
                    # TODO: v13+ accounting, deal with unbalanced credit issues
                    inv_line.update({'quantity': update_qty})
                    self._onchange_invoice_line_ids()

        return picking_id, picking_type_id
