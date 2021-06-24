# -*- coding: utf-8 -*-

from odoo import models, fields, api
import pytz
from datetime import datetime, timedelta, time
from dateutil import rrule
from dateutil.relativedelta import relativedelta
import calendar as cal
from babel.dates import format_datetime
from odoo.tools.misc import get_lang

class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    django_id = fields.Char(string='Django Id')

    def api_create(self, name, email, phone, bill_to_address, ship_to_address):
        vals  = {
            'name': name,
            'phone' : phone,
            'email': email,
            'company_type': 'company'
        }
        new_res_partner = self.sudo().create(vals)
        self.create_individual_by_json_and_assign_parent(bill_to_address, new_res_partner)
        self.create_individual_by_json_and_assign_parent(ship_to_address,new_res_partner)
        return new_res_partner

    def create_individual_by_json_and_assign_parent(self, email, phone, address_json, new_res_partner):
        country_id = self.env['res.country'].search([('code', '=', address_json.get('country_code'))]).id or 233
        state_id = self.env['res.country.state'].search([('code', '=', address_json.get('state')), ('country_id', '=', country_id) ]).id or None
        parent_id = None
        if new_res_partner:
            parent_id = new_res_partner
        vals  = {
            'django_id': address_json.get('id'),
            'name': address_json.get('name'),
            'street': address_json.get('line_1'),
            'street2': address_json.get('line_2'),
            'zip': address_json.get('zipcode'),
            'city': address_json.get('city'),
            'country_id': country_id,
            'state_id': state_id,
            'parent_id': parent_id,
            'company_type': 'person',
            'email': email,
            'phone': phone
        }
        print("create_individual_by_json_and_assign_parent")
        print(vals)
        new_res_partner = self.sudo().create(vals)
        return new_res_partner

    def update_individual_by_json(self, address_json):
        partner_obj = self.sudo().search([('django_id', '=', address_json.get('id'))])
        
        country_id = self.env['res.country'].search([('code', '=', address_json.get('country_code'))]).id or 233
        state_id = self.env['res.country.state'].search([('code', '=', address_json.get('state')), ('country_id', '=', country_id) ]).id or None
        vals  = {
            'django_id': address_json.get('id'),
            'name': address_json.get('name'),
            'street': address_json.get('line_1'),
            'street2': address_json.get('line_2'),
            'zip': address_json.get('zipcode'),
            'city': address_json.get('city'),
            'country_id': country_id,
            'state_id': state_id,
            'company_type': 'person'
        }

        partner_obj.sudo().write(vals)

    def check_bill_or_ship_to_adddress(self, parent_obj, address_json, is_bill):
        partner_obj = self.sudo().search([('django_id', '=', address_json.get('id')),
                                                    ('parent_id', '=', parent_obj.id)
                                                    ])
        if len(partner_obj) == 0:
            self.create_individual_by_json_and_assign_parent(address_json, parent_obj)
        else:
            self.update_individual_by_json(address_json)


    def api_update(self, customer_id, name, email, phone, bill_to_address, ship_to_address):
        print("api_update3324234s2")
        print(customer_id)
        print(name)
        print(phone)
        print(email)
        partner_obj = self.browse(customer_id)
        vals  = {
            'name': name,
            'phone' : phone,
            'email': email,
            'company_id': 1
        }
        partner_obj.sudo().write(vals)
        self.check_bill_or_ship_to_adddress(partner_obj, bill_to_address, is_bill=True)
        self.check_bill_or_ship_to_adddress(partner_obj, ship_to_address, is_bill=False)