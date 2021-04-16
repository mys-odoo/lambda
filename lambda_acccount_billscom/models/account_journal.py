# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, registry, _
from .billscom_request import BillscomRequest

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    billscom_id = fields.Char(string='Bills.com ID', readonly=True, copy=False)

    @api.model
    def _get_BillscomRequest(self, username, password, orgid, devkey, prod):
        return BillscomRequest(username, password, orgid, devkey, prod)

