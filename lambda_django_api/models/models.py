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
        print(new_res_partner)
        self.create_individual_by_json_and_assign_parent(bill_to_address, new_res_partner)
        self.create_individual_by_json_and_assign_parent(ship_to_address,new_res_partner)
        return new_res_partner

    def create_individual_by_json_and_assign_parent(self, address_json, new_res_partner):
        print("create_individual_by_json_and_assign_parent")
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
            'parent_id': new_res_partner.id,
            'company_type': 'person'
        }
        new_res_partner = self.sudo().create(vals)
        return new_res_partner

    def check_bill_or_ship_to_adddress(self, parent_obj, address_json, is_bill):
        partner_obj = self.sudo().search([('django_id', '=', address_json.get('id')),
                                                    ('parent_id', '=', parent_obj.id)
                                                    ])
        print("check_bill_or_ship_to_adddress")
        print(partner_obj)
        print(address_json.get('id'))
        print(parent_obj.id)
        if len(partner_obj) == 0:
            self.create_individual_by_json_and_assign_parent(address_json, parent_obj)