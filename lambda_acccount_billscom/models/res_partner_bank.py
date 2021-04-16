# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    is_savings = fields.Boolean(string='Is Savings Account ?')
    is_personal_acct = fields.Boolean(string='Is Personal Account ?')

