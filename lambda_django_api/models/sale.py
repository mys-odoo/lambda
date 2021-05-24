# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    django_so_id = fields.Char(string='Id')
    django_purchase_order_id = fields.Char(string='PO Id')
    django_purchase_order_terms = fields.Char(string='Purchase Order Terms')
    pdf_url = fields.Char(string='PDF URL')
    build_sheet_url = fields.Char(string='Sheet URL')

    attachment_count = fields.Integer('# Image', compute='_compute_attachment_count')

    def _compute_attachment_count(self):
        attachment_data = self.env['ir.attachment'].sudo().search([('res_model', '=', 'sale.order'), ('res_id', '=', self.id), ])
        self.attachment_count = len(attachment_data)
    
    def action_attachment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_attachment")
        action['context'] = {
            'default_res_model': self._name,
            'default_res_id': self.ids[0]
        }
        action['domain'] = ['&', ('res_model', '=', 'sale.order'), ('res_id', 'in', self.ids)]
        return action