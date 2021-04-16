# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta


from odoo import models, fields, api, registry, _
from odoo.exceptions import UserError, ValidationError

from odoo.tools.misc import split_every
from .billscom_request import BillscomRequest


_logger = logging.getLogger(__name__)
_pp = pprint.PrettyPrinter(indent=4)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    billscom_id = fields.Char(string='Bills.com ID', readonly=True, copy=False)

    @api.model
    def _get_BillscomRequest(self, username, password, orgid, devkey, prod):
        return BillscomRequest(username, password, orgid, devkey, prod)


    def _get_account_jounral(self, request, billscom_journal_id):
        '''
        Their is not API endpoint for querying Bank Account detailes
        so we will back read BankAccount using Is on payment
        and update them on Journal using Name of the Journal 
        this will help in persisting relation between journal 
        and bank over the time
        '''
        journal_noprefetch = self.env['account.journal'].with_context(prefetch_fields=False)
        journal = journal_noprefetch.search([('billscom_id', '=', billscom_journal_id)], limit=1)
        if journal:
            _logger.info('Found Journal "%s" with Bills.com Id "%s" using it'%(journal.name, billscom_journal_id))
            return journal
        else:
            data = {'id': billscom_journal_id}
            bank_detail = request._make_api_request('Crud/Read/BankAccount.json', data)

            if bank_detail:
                bank_name = bank_detail['bankName']
                src_journal = journal_noprefetch.search([('name', '=', bank_name)], limit=1)
                if src_journal:
                    _logger.info('Found Journal "%s" with Id "%s"'%(bank_name, src_journal.id))
                    src_journal.write({'billscom_id': bank_detail['id']})
                    return src_journal
                else:
                    _logger.warning('No Journal found for Bank "%s"'%(bank_name))
            else:
                _logger.warning('Could not find any bank with Bills.com Id "%s"'%(billscom_journal_id))

        return False

    @api.model
    def _check_bills_payment(self, use_new_cursor=True, company_id=None):
        """
        Check payments on bills.com
        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
            100 bills.
        This is appropriate for batch jobs.
        """
        self = self.with_company(company_id)

        company = self.env.company
        if not company.is_billscom_configured:
            _logger.error('Bills.com crendetails are not configured, skiping cron execution')
        username = company.billscom_username
        password = company.billscom_password
        orgid = company.billscom_orgid
        devkey = company.billscom_devkey
        prod  = company.billscom_prod
        request = self._get_BillscomRequest(username, password, orgid, devkey, prod)

        partner_noprefetch = self.env['res.partner'].with_context(prefetch_fields=False)
        account_noprefetch = self.env['account.account'].with_context(prefetch_fields=False)

        domain = [
            ('state', '=', 'posted'),
            ('billscom_id', '!=', False),
            ('move_type', '=', 'in_invoice'),
        ]
        moves_noprefetch = self.search_read(domain, fields=['id', 'billscom_id'])
        moves_noprefetch = {
            move['billscom_id']: move['id'] for move in moves_noprefetch
        }
        if use_new_cursor:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))
        try:
            filters = [{
                'field': 'updatedTime', 
                'op': '>=', 
                'value': (datetime.now()-relativedelta(days=10)).isoformat(),
            }]
            search_result = request.list_objects('SentPay', 0, 100, filters, raise_source_exception=True)
            for sentpay in search_result:
                partner = partner_noprefetch.search([('billscom_id', '=', sentpay['vendorId'])], limit=1)
                if not partner:
                    _logger.warning('skipping vendor payment creation with reference "%s" as vendor not found in system'%(sentpay['name']))
                    continue
                account = account_noprefetch.search([('billscom_id', '=', sentpay['chartOfAccountId'])], limit=1)
                if not account:
                    _logger.warning('skipping vendor payment creation with reference "%s" as mapping account not found in system'%(sentpay['name']))
                    continue
                journal = self._get_account_jounral(request, sentpay['bankAccountId'])
                if not journal:
                    _logger.warning('skipping vendor payment creation with reference "%s" as mapping Journal for bank not found in system'%(sentpay['name']))
                    continue
                fields = [
                    'payment_type', 'partner_type', 'state', 'destination_account_id',
                    'journal_id'
                ]
                payment_vals = self.with_context({
                        'default_payment_type': 'outbound',
                        'default_partner_type': 'supplier',
                        'default_move_journal_types': ('bank', 'cash')
                    }).default_get(fields)
                payment_vals.update({
                        'journal_id': journal.id,
                        'destination_account_id': account.id,
                        'partner_id': partner.id,
                        'amount': sentpay['amount'],
                        'date': sentpay['processDate'],
                        'billscom_id': sentpay['id'],
                        'name': sentpay['name'],
                        'ref': sentpay['name'],
                        'payment_method_id': journal.outbound_payment_method_ids[0].id,
                        'currency_id': journal.currency_id.id or journal.company_id.currency_id.id,
                    })
                payment_id = self.with_context({
                        'default_payment_type': 'outbound',
                        'default_partner_type': 'supplier',
                        'default_move_journal_types': ('bank', 'cash')
                    }).create(payment_vals)
                payment_id.action_post()
                if use_new_cursor:
                    cr.commit()
        except Exception as ex:
             _logger.error(traceback.format_exc())
            if use_new_cursor:
                cr.rollback()
            else:
                raise
        if use_new_cursor:
            cr.close()
        return {}