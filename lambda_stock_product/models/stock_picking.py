# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import pdf

import logging
import base64
import io

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        result = super(StockPicking, self)._action_done()
        
        if self.sale_id and (self.sale_id.state == 'sale' or self.sale_id.state == 'done'):
            amvs = pick.sale_id._create_invoices()
            for amv in amvs:
                amv.action_post()
                
        if self.picking_type_id.sequence_code == "OUT":
            for picking in self:
                pdfs = []

                attachment = self.env['ir.attachment'].search([('res_id', '=', picking.id)])
                if attachment:
                    pdfs.append(base64.decodebytes(attachment.datas))
                    self.sale_id.message_post(
                        attachments=[("{}.pdf".format(attachment.name), base64.decodebytes(attachment.datas))],
                        body="Shipping Label:",
                    )

                stock_model = self.env.ref('stock.action_report_delivery', raise_if_not_found=True)
                delivery_slip_pdf, _ = stock_model._render_qweb_pdf(self.id)
                pdfs.append(delivery_slip_pdf)

                inv_model = self.env.ref('account.account_invoices', raise_if_not_found=True)
                for inv in self.sale_id.invoice_ids:
                    inv_pdf, _ = inv_model._render_qweb_pdf(inv.id)
                    pdfs.append(inv_pdf)
                    picking.sale_id.message_post(
                        attachments=[("{}.pdf".format(inv.name), inv_pdf)],
                        body="Invoice:",
                    )

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
        return result