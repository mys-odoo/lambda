# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pprint
import logging
import datetime
import requests
from werkzeug.urls import url_join

from odoo import fields,_
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_is_zero


_logger = logging.getLogger(__name__)
_pp = pprint.PrettyPrinter(indent=4)

class BillscomRequest():
    '''
    Implementation of Bills.com API
    https://developer.bill.com/hc/en-us/articles/360035429991-About-the-Developer-Program
    '''


    def __init__(self, username, password, orgid, devkey, prod_environment, debug_logger=True):
        self.debug_logger = debug_logger
        # Product and Testing url
        self.endurl = 'https://api.bill.com/api/v2/'
        if not prod_environment:
            self.endurl = 'https://api-sandbox.bill.com/api/v2/'

        # Basic detail require to authenticate
        self.username = username
        self.password = password
        self.orgid = orgid
        self.devkey = devkey

    def _make_api_request(self, endpoint, data=None, raise_source_exception=True):
        '''
        make an bills.com api call, request/response
        https://developer.bill.com/hc/en-us/articles/360035447551-API-Structure
        All API requests use the HTTP POST method.

        '''
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        access_url = url_join(self.endurl, endpoint)
        auth_url = url_join(self.endurl, 'Login.json')
        if data == None:
            data = {}
        try:
            auth_params = {
                'userName': self.username,
                'password': self.password,
                'orgId': self.orgid,
                'devKey': self.devkey,
            }
            auth_response = requests.post(auth_url, data=auth_params, headers=headers)
            auth_response = auth_response.json()
            if auth_response.get('response_status') != 0:
                msg  = _('Bills.com authentication faied with an error with code %s: \n%s')%(
                            auth_response['response_data']['error_code'],
                            auth_response['response_data']['error_message'])
                raise UserError(msg)
            auth_session = auth_response.get('response_data')

            data_payload = {
                'devKey': self.devkey,
                'sessionId': auth_session['sessionId'],
                'data': json.dumps(data),
            }
            response = requests.post(access_url, data=data_payload, headers=headers)
            response = response.json()
            if raise_source_exception and response.get('response_status') != 0:
                msg  = 'Billscom returned an error with code %s: \n%s'%(
                            response['response_data']['error_code'],
                            response['response_data']['error_message'])
                raise UserError(_(msg))
            if not raise_source_exception:
                return response
            return response.get('response_data')
        except Exception as e:
            raise e

    def list_objects(self, object_name, start, maxsize=100, filters=[], sort=[], nested=True, raise_source_exception=True):
        '''
        List operation retrieve instances of an entity. 
        The result contains objects that match the request,
        including all fields. The data can be paginated, filtered and sorted.
        https://developer.bill.com/hc/en-us/articles/210136993-List

        '''
        data={
          'nested' : nested,
          'start' : start,
          'max' : maxsize,
          'filters' : filters,
          'sort' : sort,
        }
        uri = 'List/%s.json'%(object_name)
        response = self._make_api_request(uri, data=data, raise_source_exception=raise_source_exception)
        return response


    def search_objects(self, term, entity, raise_source_exception=True):
        '''
        Search Any valid bills.com object with search term
        https://developer.bill.com/hc/en-us/articles/210136643-SearchEntity

        '''
        data = {
           'term' : term, 
           'entity' : entity, 
        }
        response = self._make_api_request('SearchEntity.json', data=data, raise_source_exception=raise_source_exception)
        return response


    def _partner_split_name(self, partner_name, raise_source_exception=True):
        return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


    def find_accounts(self, account, raise_source_exception=True):
        filters = [{
            'field': 'name', 
            'op': '=', 
            'value': account.name,
        }]
        search_result = self.list_objects('ChartOfAccount', 0, 1, filters, raise_source_exception=raise_source_exception)
        return search_result


    def manage_vendor(self, partner, raise_source_exception=True):
        '''
        API Vendor Management
        https://developer.bill.com/hc/en-us/articles/209605773-Vendor
        '''
        uri = 'Crud/Create/Vendor.json'

        contact_rec = {
            'entity' : 'Vendor',
            'isActive' : '1',
            'name' : partner.name,
            'nameOnCheck' : partner.name,
            'companyName' : partner.company_name or '',
            'accNumber': partner.ref or '',
            'taxId' : partner.vat or '',
            'track1099' : partner.track_1099,
            'address1' : partner.street or '',
            'address2' : partner.street2 or '',
            'addressCity' : partner.city or '',
            'addressState' : partner.state_id.code if partner.state_id else '',
            'addressZip' : partner.zip or '',
            'addressCountry' : partner.country_id.name if partner.country_id else '',
            'email' : partner.email or '',
            'phone' : partner.phone or '',
            'paymentEmail' : partner.email or '',
            'paymentPhone' : partner.phone or '',
            'description' : partner.comment or '',
            'accountType' :  '1' if partner.company_type == 'company' else '2'
        }
        # Add contact person details
        names = self._partner_split_name(partner.name)
        contact_rec.update({
            'contactFirstName': names[0],
            'contactLastName': names[1],
        })
        # Add invoicing contact email and phone for billing address 
        if partner != partner.commercial_partner_id:
            contact_rec.update({'companyName' : partner.commercial_partner_id.name})
        elif partner == partner.commercial_partner_id and partner.company_type == 'company':
            contact_rec.update({'companyName' : partner.name})
        if partner.billscom_id:
            contact_rec.update({'id' : partner.billscom_id})
            uri = 'Crud/Update/Vendor.json'
            raise_source_exception = False

        data={'obj' : contact_rec}
        response = self._make_api_request(uri, data=data, raise_source_exception=raise_source_exception)
        if not raise_source_exception and response.get('response_status') != 0:
            if response.get('response_data', {}).get('error_code') == 'BDC_1205':
                uri = 'Crud/Create/Vendor.json'
                data['obj'].pop('id')
                raise_source_exception = True
                response = self._make_api_request(uri, data=data, raise_source_exception=raise_source_exception)
            else:
                msg  = 'Billscom returned an error with code %s: \n%s'%(
                            response['response_data']['error_code'],
                            response['response_data']['error_message'])
                raise UserError(_(msg))
        if not raise_source_exception:
            response = response.get('response_data')
        return response

    def create_bill(self, bill, raise_source_exception=True):
        '''
        https://developer.bill.com/hc/en-us/articles/208155326-Bill
        '''
        # upsert vendor to make sure we can create bills
        result = self.manage_vendor(bill.partner_id, raise_source_exception=raise_source_exception)
        bill.partner_id.write({'billscom_id': result['id']})
        body = _('Successfully validated bill vendor persist in Bills.com with id "%s"')%(result['id'])
        bill.message_post(subject='Bills.com', body=body, message_type='comment', subtype_xmlid='mail.mt_comment')
        bill.partner_id.flush()
        invoice_lines = []
        for line in bill.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
            invoice_lines.append({
                'entity': 'BillLineItem',
                'amount': line.price_total,
                'chartOfAccountId': line.account_id.billscom_id,
                'description': line.name,
                'quantity': line.quantity,
                'unitPrice': line.price_unit,
            })
        invoice_val = {
            'entity': 'Bill',
            'isActive': '1',
            'vendorId': bill.partner_id.billscom_id,
            'invoiceNumber': bill.name,
            'invoiceDate': fields.Date.to_string(bill.invoice_date) if bill.invoice_date else '',
            'dueDate': fields.Date.to_string(bill.invoice_date_due) if bill.invoice_date_due else '',
            'glPostingDate': fields.Date.to_string(bill.date) if bill.date else '',
            'description': bill.narration or '',
            'poNumber': bill.purchase_id.name if bill.purchase_id else (bill.ref or ''),
            'billLineItems' : invoice_lines
        }
        data={'obj' : invoice_val}
        result = self._make_api_request('Crud/Create/Bill.json', data=data)
        return result