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

    def api_create(self, address_json, email, phone):
        country_id = self.env['res.country'].search([('code', '=', address_json.get('country_code'))]).id or 233
        state_id = self.env['res.country.state'].search([('code', '=', address_json.get('state')), ('country_id', '=', country_id) ]).id or None
        vals  = {
            'name': address_json.get('name'),
            'street': address_json.get('line_1'),
            'street2': address_json.get('line_2'),
            'zip': address_json.get('zipcode'),
            'city': address_json.get('city'),
            'country_id': country_id,
            'state_id': state_id,
            'phone' : phone,
            'email': email,
        }
        new_res_partner = self.sudo().create(vals)
        return new_res_partner