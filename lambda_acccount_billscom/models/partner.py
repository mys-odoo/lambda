# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .billscom_request import BillscomRequest


_logger = logging.getLogger(__name__)



class Partner(models.Model):

    _inherit = 'res.partner'


    billscom_id = fields.Char(string='Bills.com ID', readonly=True)
    track_1099 = fields.Boolean(string='Track 1099')

    @api.model
    def _get_BillscomRequest(self, username, password, orgid, devkey, prod):
        return BillscomRequest(username, password, orgid, devkey, prod)

    def upsert_vendor(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        if not company.is_billscom_configured:
            raise ValidationError(_('Bills.com crendetails are not configured.'))
        username = company.billscom_username
        password = company.billscom_password
        orgid = company.billscom_orgid
        devkey = company.billscom_devkey
        prod  = company.billscom_prod
        request = self._get_BillscomRequest(username, password, orgid, devkey, prod)
        result = request.manage_vendor(self)
        if result:
            self.write({'billscom_id': result['id']})
        else:
            raise UserError(_('Received unexpected results, please try again.'))
        title = _('Succeeful Created/Updated Vendor')
        message = _('Succeefully created or updated Vendor "%s" in Bills.com with id "%s". \n'\
                    'Please save and refresh to see the udpates.'%(self.name, result['id']))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
            }
        }