# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .billscom_request import BillscomRequest


class AccountAccount(models.Model):

    _inherit = 'account.account'

    billscom_id = fields.Char(string='Bills.com ChartofAccounts Id', readonly=True,
                                help='Id used for Bills reporting to bills.com. To lookup ChartofAccounts'\
                                    ' to Bills.com click button "Bills.com" lookup to link record with Bills.com')

    @api.onchange('name')
    def onchange_account_name(self):
        self.billscom_id = False

    @api.model
    def _get_BillscomRequest(self, username, password, orgid, devkey, prod):
        return BillscomRequest(username, password, orgid, devkey, prod)

    def linkto_billscom(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        if not company.is_billscom_configured:
            raise ValidationError(_('Bills.com crendetails are not configured.'))
        username = company.billscom_username
        password = company.billscom_password
        orgid = company.billscom_orgid
        devkey = company.billscom_devkey
        prod  = company.billscom_prod
        request = self._get_BillscomRequest(username, password, orgid, devkey, prod)
        result = request.find_accounts(self)
        if result:
            self.write({'billscom_id': result[0]['id']})
        else:
            raise UserError(_('No account found matching "%s" in Bills.com, please make sure '\
                            'you have account created with same in Bills.com ChartofAccounts')%(self.name))
        title = _('Succeefully linked ChartofAccounts')
        message = _('Succeefully linked ChartofAccounts "%s" from Bills.com with id "%s". \n'\
                    'Please save and refresh to see the udpates.'%(self.name, result[0]['id']))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
            }
        }