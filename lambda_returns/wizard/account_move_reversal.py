# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        # If there are multiple bills with same reference string, add a number to the end for multiples
        existing_bills = self.env['account.move'].search([('ref', '=like', res['ref'] + '%')])
        if existing_bills:
            res['ref'] = res['ref'] + '(%s)' % str(len(existing_bills))
        return res
