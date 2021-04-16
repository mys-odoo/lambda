# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _


_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    billscom_username = fields.Char(related='company_id.billscom_username',
                                        string='Bills.com Username', readonly=False)
    billscom_password = fields.Char(related='company_id.billscom_password',
                                        string='Bills.com Password', readonly=False)
    billscom_orgid = fields.Char(related='company_id.billscom_orgid',
                                        string='Bills.com Organization ID', readonly=False)
    billscom_devkey = fields.Char(related='company_id.billscom_devkey',
                                        string='Bills.com Developer Key', readonly=False)
    billscom_prod = fields.Boolean(related='company_id.billscom_prod',
                                        string='Bills.com Production Credentails', readonly=False)

