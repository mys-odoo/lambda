# -*- coding: utf8 -*-
from odoo import http
from odoo.http import request
from odoo import api, SUPERUSER_ID
import logging
import json
import traceback
from odoo.exceptions import AccessDenied
from odoo.addons.web.controllers.main import Session

_logger = logging.getLogger(__name__)

PAGE = 1

db_list = http.db_list

db_monodb = http.db_monodb

def ensure_db(redirect='/web/database/selector'):
    db = request.params.get('db') and request.params.get('db').strip()

    if db and db not in http.db_filter([db]):
        db = None
    if not db:
        print(request.httprequest)
        db = db_monodb(request.httprequest)
    return db


class SessionAuthenticate(Session):
    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        res = super(SessionAuthenticate, self).authenticate(db, login, password, base_location)
        request.session.authenticate(db, login, password)
        return res

class SyncoriaApi(http.Controller):
    @http.route('/api/login', type='json', auth="public")
    def api_login(self, csrf=False, **kwargs):
        res = {
            'meta': {
                'status': False,
                'message': None
            },
            'data': {
            }
        }
        try:
            values = json.loads(request.httprequest.data)
            db = values.get('db', False) or ensure_db() or False
            if db:
                if db in http.db_list():
                    login = values.get('login', False)
                    password = values.get('password', False)
                    print(login)
                    print(password)
                    if login!= "" and password!= "":
                        user = request.env['res.users'].syncoria_login(db, login, password)   

                        if user:
                                res['meta'].update({
                                    'status': True,
                                    'message': 'Login successfull.'
                                })
                                res['data'].update({
                                    "token": user.token,
                                    "db": db,
                                    "expire": user.date_expire,
                                })
                                return res
                        else:
                            res['meta'].update({
                                "status_code": 401,
                                'message': "Username or password is incorrect. Please try again."})
                    else:
                        res['meta'].update({
                            "status_code": 403,
                            'message': "Username or password is missing. Please check again."
                        })
                else:
                    res['meta'].update({
                        "status_code": 404,
                        "message": "No database found on server. Contact the manager or the system administrator."
                    })
            else:
                res['meta'].update({
                    "status_code": 401,
                    'message': "Please enter the database."})
        except AccessDenied:
            res['meta'].update({
                'status': False,
                "status_code": 401,
                'message': "Authenticate informations not correct. Please check again."
            })
        except Exception as error:
            res['meta'].update({'message': error})
            _logger.info("\n%s", traceback.format_exc())
            pass
        return res
    
    @http.route('/api/logout', type='json', auth="public")
    def api_logout(self, csrf=False, **kwargs):
        res = {
            'meta': {
                'status': False,
                'message': None
            },
            'data': {}
        }
        token = request.httprequest.environ.get('HTTP_TOKEN', False)
        user = request.env['res.users'].check_token(token)
        if not user or not token:
            res['meta'].update({
                "status_code": 403,
                'message': 'Could not authenticate this account. Please check token again.',
            })
            return res
        user.with_user(SUPERUSER_ID).write({
            'token': False,
            'date_expire': False,
        })
        
        res['meta'].update({
            'status': True,
            'message': "Logout successfull."
        })
        return res
    