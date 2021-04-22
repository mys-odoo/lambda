# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        picking_id, picking_type_id = super(ReturnPicking, self)._create_returns()

        # Get the return picking (Transfer Receipt)
        pick = self.env['stock.picking'].browse(picking_id)

        # Only create returns for returns on receipts
        if pick.picking_type_id.code == 'outgoing':
            inv_ids = pick.purchase_id.invoice_ids.filtered(lambda i: i.state == 'posted' and not i.reversed_entry_id)

            # group the SML into bills that have the sml's product
            bills = {inv.id: self.env['stock.move.line'] for inv in inv_ids}

            for sml in pick.move_line_ids_without_package:
                matching_inv = inv_ids.filtered(lambda i: sml.product_id in i.invoice_line_ids.product_id)
                if matching_inv:
                    bills[matching_inv[0].id] += sml

            for inv_id in bills:
                # Create a credit note for each bill that has the sml from the return pick
                if bills[inv_id]:
                    reversal = self.env['account.move.reversal'].create({
                        'move_ids': [(4, inv_id, 0)],
                        'refund_method': 'refund',
                    })
                    res = reversal.reverse_moves()
                    credit_note = self.env['account.move'].search([('reversed_entry_id', '=', inv_id)],
                                                                  order='create_date desc', limit=1)
                    # Update the lines in the credit note to match amount from return, else zero it
                    changed_lines = []
                    for inv_line in credit_note.invoice_line_ids:
                        move_line = bills[inv_id].filtered(lambda ml: ml.product_id == inv_line.product_id)
                        if move_line:
                            changed_lines.append((1, inv_line.id, {'quantity': move_line.product_uom_qty}))
                        else:
                            changed_lines.append((2, inv_line.id, 0))

                    credit_note.write({'invoice_line_ids': changed_lines})
                    credit_note._onchange_invoice_line_ids()
        return picking_id, picking_type_id
