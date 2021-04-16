# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bills.com Vendors & Payment Intgeration',
    'author': 'Odoo Inc',
    'website': 'http://www.odoo.com',
    'category': 'Professional Services/Odoo, Inc',
    'license': 'OEEL-1',
    'version': '0.1',
    'summary': 'Bills.com Vendor and Payment Intgeration',
    'description': '''
Bills.com Vendors Intgeration
======================================

This module manages approval vendor and payment intgeration
    ''',
    'depends': ['account', 'contacts'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/partner_view.xml',
        'views/res_bank_views.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'data/account_payment_data.xml',
    ],
    'demo':[
    ],
    'qweb': [
    ],
}
