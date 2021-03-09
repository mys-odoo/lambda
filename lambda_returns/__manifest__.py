# -*- coding: utf-8 -*-
{
    'name': "Lambda: Returns",

    'summary': """
        streamline the return process.""",

    'description': """
    Task ID: 2424938 - CIC
        Requirement 1 - Generate a credit note automatically with qty on the return
Once a return is generated on delivery, we’d like a credit note to be created automatically with quantities of products on the return.


Requirement 2 - Return qty on PO
If we create more than one return on a delivery order - we’d like all the quantities to be recognized on the respective PO, not only the quantities of the first return.


    """,

    'author': "Odoo Inc.",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Custom Development',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock', 'purchase_stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        # 'views/templates.xml',
    ],
}
