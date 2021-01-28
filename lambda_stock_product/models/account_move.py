# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post_and_print(self):
        self.action_post()
        return self.env.ref('account.account_invoices').report_action(self)
