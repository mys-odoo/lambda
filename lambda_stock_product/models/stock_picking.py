# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import pdf

import base64
import io

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        result = super(StockPicking, self)._action_done()
        if self.picking_type_id.sequence_code == "OUT":
            for picking in self:
                pdfs = []

                attachment = self.env['ir.attachment'].search([('res_id', '=', picking.id)])
                try:
                    pdfs.append(base64.decodebytes(attachment.datas))
                except:
                    pass

                delivery_slip = self.env.ref('stock.action_report_delivery', raise_if_not_found=True)
                delivery_slip_pdf, _ = delivery_slip._render_qweb_pdf(self.id)
                pdfs.append(delivery_slip_pdf)

                inv = self.env.ref('account.account_invoices', raise_if_not_found=True)
                inv_pdf, _ = inv._render_qweb_pdf(self.sale_id.invoice_ids.ids)
                pdfs.append(inv_pdf)

                merged_pdf = pdf.merge_pdf(pdfs)
                
                picking.message_post(
                    attachments=[("Delivery_Combined_{}.pdf".format(picking.name), merged_pdf)],
                    body="Merged document of delivery slip, shipping label, and invoice.",
                )
        return result

    def custom_button_validate(self):
        if not self.picking_type_id.sequence_code == "OUT":
            return self.button_validate()
        return {
            'name': 'Delivery Warning Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'views': [[self.env.ref('lambda_stock_product.view_stock_picking_wizard_lambda').id, 'form']],
            'target': 'new',
        }

    def action_save_then_validate(self):
        for mv in self.move_ids_without_package:
            mv.product_id.write({
                'weight': mv.weight,
                'volume': mv.volume
            })
        self.write({
            'carrier_id': self.carrier_id
        })
        result = self.button_validate()
        # self.env.ref('stock.action_report_delivery').report_action(self)
        return result

    @api.depends('move_type', 'immediate_transfer', 'move_lines.state', 'move_lines.picking_id')
    def _compute_state(self):
        super(StockPicking, self.sudo())._compute_state()
        if self.state == 'done':
            if self.sale_id and (self.sale_id.state == 'sale' or self.sale_id.state == 'done'):
                amvs = self.sale_id._create_invoices()
                for amv in amvs:
                    amv.action_post_and_print()
            # self.env.ref('stock').report_action(self)