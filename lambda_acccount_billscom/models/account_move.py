# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta


from odoo import models, fields, api, registry, _
from odoo.exceptions import UserError, ValidationError

from odoo.tools.misc import split_every
from .billscom_request import BillscomRequest


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    billscom_id = fields.Char(string='Bills.com ID', readonly=True, copy=False)
    skip_billscom = fields.Boolean(string='Skip Posting to Bills.com', readonly=True,
                            states={'draft': [('readonly', False)]}, copy=False,
                            help='If checked then this bill not be reported ot Bills.com, '\
                                'this allows manaul or auatomed expectation using automed actions')

    @api.model
    def _get_BillscomRequest(self, username, password, orgid, devkey, prod):
        return BillscomRequest(username, password, orgid, devkey, prod)

    def action_post(self):
        result = super(AccountMove, self).action_post()
        self.filtered(lambda inv:inv.move_type in ('in_invoice', 'in_receipt') and not inv.skip_billscom)._send_bill()
        return result 


    def _send_bill(self):
        usd_cur = self.env.ref('base.USD')
        except_bills = self.filtered(lambda bill: bill.currency_id != usd_cur or bill.company_currency_id != usd_cur)
        if except_bills:
            raise ValidationError(_('Bill(s) %s can not be reported to Bills.com as their currency is not USD. '
                                    'Bills.com accepts bills in USD only, please mark them "Skip Posting to Bills.com"'
                                    ' to continue reporting.')% (', '.join([ bill.name for bill in except_bills ])))

        company = self.company_id or self.env.company
        if not company.is_billscom_configured:
            raise ValidationError(_('Bills.com crendetails are not configured.'))
        username = company.billscom_username
        password = company.billscom_password
        orgid = company.billscom_orgid
        devkey = company.billscom_devkey
        prod  = company.billscom_prod
        request = self._get_BillscomRequest(username, password, orgid, devkey, prod)

        for bill in self:
            #pre check all requirment and throw configuration to users
            msg = ''
            for line in bill.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
                if not line.account_id.billscom_id:
                    msg += _('- Invoices line account "%s" is not linked with Bills, this prevent '\
                            'reporting of bills, please make sure the account is linked with '\
                            'Bills.com account from Chart of Acounts view.')
            if msg:
                msg = _('The bills can not be reported to Bills.com. Please review following '\
                        'configuration issues to continue posting bills or the bills can be '
                        'marked "Skip Posting to Bills.com" to skip posting this bills to bills.com\n\n') + msg
                raise ValidationError(msg)
        
            result = request.create_bill(bill)
            if result:
                self.write({'billscom_id': result['id']})
                body = _('Successfully validated if Bill vendor "%s" persist in Bills.com and '
                        'posted bill with Id "%s"')%(bill.partner_id.name, result['id'])
                bill.message_post(subject='Bills.com', body=body, message_type='comment', subtype_xmlid='mail.mt_comment')
            else:
                raise UserError(_('Receoved unexpected results, please try again.'))
            return True
