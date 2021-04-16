# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    billscom_username = fields.Char(string='Bills.com Username')
    billscom_password = fields.Char(string='Bills.com Password')
    billscom_orgid = fields.Char(string='Bills.com Organization ID')
    billscom_devkey = fields.Char(string='Bills.com Developer Key')
    billscom_prod = fields.Boolean(string='Production Credentails')
    is_billscom_configured = fields.Boolean(compute='_compute_is_billscom_configured',
                                            help='If Checked all Communication will be done to Production Enviroment on Bills.com assuming above given credentails are valid for Bills.com.')

    @api.depends('billscom_username', 'billscom_password', 'billscom_orgid', 'billscom_devkey')
    def _compute_is_billscom_configured(self):
        for company in self:
            company.is_billscom_configured = company.billscom_username and company.billscom_password \
                                            and company.billscom_orgid and company.billscom_devkey