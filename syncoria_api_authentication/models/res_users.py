from odoo import api, fields, models
from odoo import http, SUPERUSER_ID
from odoo.addons.web.controllers.main import ensure_db
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from dateutil.relativedelta import relativedelta
import hashlib

class ResUsers(models.Model):
    _inherit = "res.users"
    
    token = fields.Char('Token', copy=False)
    date_expire = fields.Datetime(string='Token Expire')
    
    def syncoria_login(self, db, login, password):
        res = False
        uid = self.with_user(SUPERUSER_ID).authenticate(db, login, password, False)
        if uid:
            user = self.with_user(SUPERUSER_ID).browse(uid)
            res = '%s-%s' % (user.login, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            res = res.encode('utf-8')
            hash_object = hashlib.sha512(res)
            res = hash_object.hexdigest()
            user.with_user(SUPERUSER_ID).write({
                'token': res,
                'date_expire': (datetime.now() + relativedelta(hours=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            })
            return user
    
    def check_token(self, token):
        res = False
        if token:
            user = self.with_user(SUPERUSER_ID).search([('token', '=', token)])
            if user:
                date_expire = datetime.strptime(str(user.date_expire), DEFAULT_SERVER_DATETIME_FORMAT)
                print(date_expire, DEFAULT_SERVER_DATETIME_FORMAT)
                if datetime.now() < date_expire:
                    res = user
        return res






