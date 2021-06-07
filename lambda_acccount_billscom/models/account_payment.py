# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import pprint
import logging
import traceback
from datetime import datetime
from dateutil.relativedelta import relativedelta


from odoo import models, fields, api, registry, _
from odoo.exceptions import UserError, ValidationError

from odoo.tools.misc import split_every
from .billscom_request import BillscomRequest


_logger = logging.getLogger(__name__)
_pp = pprint.PrettyPrinter(indent=4)

BILLSCOM_PAID_STATUS = '2'

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    billscom_id = fields.Char(string='Bills.com ID', readonly=True, copy=False)
    billscom_paybill_id = fields.Char(string='Bills.com Paid Bill', readonly=True, copy=False)

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
    def _check_bills_payment(self, use_new_cursor=True, company_id=None, billstatus=None):
        """
        Check payments on Bills.com
        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
            100 bills.
        This is appropriate for batch jobs.
        """
        self = self.with_company(company_id)
        search_result = []
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
            ('move_type', 'in', ('in_invoice', 'in_receipt')),
        ]
        moves_noprefetch = self.search_read(domain, fields=['id', 'billscom_id'])
        moves_noprefetch = {
            move['billscom_id']: move['id'] for move in moves_noprefetch
        }
        if use_new_cursor:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))
        try:
            last_callback_datetime = (datetime.now()-relativedelta(days=10)).isoformat()

            last_date_param = self.env['ir.config_parameter'].get_param('bills.com.last.payment.check.date')
            last_callback_datetime = last_date_param if last_date_param else last_callback_datetime
            filters = [{
                'field': 'updatedTime', 
                'op': '>=', 
                'value': last_callback_datetime,
            }]
            if billstatus:
                filters.append({
                    'field': 'status',
                    'op': '=',
                    'value': billstatus,
                })
            sort = [{
                'field':'updatedTime', 
                'asc': 1,
            }]
            search_result = request.list_objects('SentPay', 0, 160, filters, sort, raise_source_exception=True)
            _logger.info('Bills.com found %d bill payment to process'%(len(search_result)))
        except Exception as ex:
            _logger.error('Bills.com api failure with following error')
            _logger.error(traceback.format_exc())
            if use_new_cursor:
                cr.rollback()
            else:
                raise
        for sentpay in search_result:
            try:
                partner = partner_noprefetch.search([('billscom_id', '=', sentpay['vendorId'])], limit=1)
                if not partner:
                    _logger.warning('skipping vendor payment creation with reference "%s" '\
                                        'as vendor not found'%(sentpay['name']))
                    continue
                account = account_noprefetch.search([('billscom_id', '=', sentpay['chartOfAccountId'])], limit=1)
                if not account:
                    _logger.warning('skipping vendor payment creation with reference "%s" as '\
                                        'mapping account not found'%(sentpay['name']))
                    continue
                journal = self._get_account_jounral(request, sentpay['bankAccountId'])
                if not journal:
                    _logger.warning('skipping vendor payment creation with reference "%s" as '\
                                        'mapping Journal for bank not found'%(sentpay['name']))
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
                        'ref': sentpay['name'],
                        'payment_method_id': journal.outbound_payment_method_ids[0].id,
                        'currency_id': journal.currency_id.id or journal.company_id.currency_id.id,
                        'billscom_id': sentpay['id'],
                    })
                if sentpay.get('status') == '3':
                    # Status  Denotes the status of the payment, where
                    # 1 = Scheduled, 2 = Done, 3 = Cancel
                    payment_vals.update({'state': 'cancel'})
                if sentpay['billPays']:
                    for billpay in sentpay['billPays']:
                        # Update paid bill reference for payment matching
                        payment_vals.update({'billscom_paybill_id': billpay['billId']})
                        #Do not create payment already created
                        existing_payment = self.search([
                                                ('billscom_id', '=', sentpay['id']),
                                                ('billscom_paybill_id', '=', billpay['billId'])
                                            ], limit=1)
                        if existing_payment:
                            if existing_payment.state == 'draft':
                                existing_payment.write(payment_vals)

                                _logger.info('Bills.com updated draft payment %d with ref "%s" '\
                                                    'bill '%(existing_payment.id, sentpay['name']))
                            if sentpay.get('status') == BILLSCOM_PAID_STATUS:
                                # Status  Denotes the status of the payment, where
                                # 1 = Scheduled, 2 = Done, 3 = Cancel
                                payment_id.action_post()
                                _logger.info('Bills.com validated payment with ref "%s" bill'%(sentpay['name']))
                            else:
                                _logger.info('Bills.com skipped payment udpate %d with ref "%s" with '\
                                                'bill as payment state is %s'%(existing_payment.id, 
                                                    sentpay['name'], existing_payment.state))
                        else:
                            payment_id = self.with_context({
                                    'default_payment_type': 'outbound',
                                    'default_partner_type': 'supplier',
                                    'default_move_journal_types': ('bank', 'cash')
                                }).create(payment_vals)
                            _logger.info('created payment with ref "%s" for bill %s'%(sentpay['name'], billpay['billId']))
                            if sentpay.get('status') == BILLSCOM_PAID_STATUS:
                                # Status  Denotes the status of the payment, where
                                # 1 = Scheduled, 2 = Done, 3 = Cancel
                                payment_id.action_post()
                else:
                    #Do not create payment already created
                    existing_payment = self.search([('billscom_id', '=', sentpay['id'])], limit=1)
                    if existing_payment:
                        if existing_payment.state == 'draft':
                            existing_payment.write(payment_vals)
                            _logger.info('Bills.com updated draft payment %d with ref "%s" '\
                                            'without bill'%(existing_payment.id, sentpay['name']))
                            if sentpay.get('status') == BILLSCOM_PAID_STATUS:
                                # Status  Denotes the status of the payment, where
                                # 1 = Scheduled, 2 = Done, 3 = Cancel
                                payment_id.action_post()
                                _logger.info('Bills.com validated payment with ref "%s" without bill'%(sentpay['name']))
                        else:
                            _logger.info('Bills.com skipped payment %d with ref "%s" without '\
                                            'bill'%(existing_payment.id, sentpay['name']))
                    else:
                        payment_id = self.with_context({
                                'default_payment_type': 'outbound',
                                'default_partner_type': 'supplier',
                                'default_move_journal_types': ('bank', 'cash')
                            }).create(payment_vals)
                        _logger.info('Bills.com created payment with ref "%s" without bill'%(sentpay['name']))
                        if sentpay.get('status') == BILLSCOM_PAID_STATUS:
                            # Status  Denotes the status of the payment, where
                            # 1 = Scheduled, 2 = Done, 3 = Cancel
                            payment_id.action_post()
                            _logger.info('Bills.com validated payment with ref "%s" without bill'%(sentpay['name']))
                self.env['ir.config_parameter'].set_param('bills.com.last.payment.check.date', sentpay['updatedTime'])
                if use_new_cursor:
                    cr.commit()
            except Exception as ex:
                _logger.error('Bills.com payment creation failed with reference "%s" '\
                                'as vendor not found'%(sentpay['name']))
                _logger.error(traceback.format_exc())
                if use_new_cursor:
                    cr.rollback()
                else:
                    raise
        if use_new_cursor:
            cr.close()
        return {}



    @api.model
    def _reconcile_bills_payments(self, use_new_cursor=True, company_id=None):
        self = self.with_company(company_id)
        if use_new_cursor:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))
        self = self.with_company(company_id)
        bills = self.env['account.move']
        reconciliation_widget = self.env['account.reconciliation.widget']
        payments = self.search([
                ('state', '=', 'posted'),
                ('billscom_id', '!=', False),
                ('billscom_paybill_id', '!=', False),
            ])
        for payment in payments:
            try:
                invoice = bills.search([
                    ('billscom_id', '=', payment.billscom_paybill_id),
                    ('move_type', 'in', ('in_invoice', 'in_receipt')),
                    ('amount_residual', '>', 0),
                    ('state', '=', 'posted'),
                    ('is_reconciled', '=', False)
                ], limit=1)
                if invoice:
                    inv_rev_ids = invoice.line_ids.filtered(lambda iv:
                                            iv.account_id.internal_type == 'payable' and
                                            iv.amount_residual < 0)
                    payment_rev_ids = payment.move_id.line_ids.filtered(lambda iv:
                                            iv.account_id.internal_type == 'payable' and
                                            iv.amount_residual > 0)
                    if inv_rev_ids and payment_rev_ids:
                        widget_id = reconciliation_widget.process_move_lines([{
                                'type': False,
                                'mv_line_ids': inv_rev_ids.ids + payment_rev_ids.ids,
                                'new_mv_line_dicts': []
                            }])
                if use_new_cursor:
                    cr.commit()
            except Exception as ex:
                _logger.error('Bills.com payment (%d) reconciliation failed with following '\
                                'error: '%(payment.id))
                _logger.error(traceback.format_exc())
                if use_new_cursor:
                    cr.rollback()
                else:
                    raise
        if use_new_cursor:
            cr.close()
        return {}