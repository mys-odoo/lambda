# -*- coding: utf-8 -*-
{
    'name': "Lambda Django APIs",

    'summary': "Lambda Django APIs",

    'description': "",

    'author': "Syncoria",
    'website': "http://www.syncoria.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'sale', 'product'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/sale.xml',
        'views/product.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    
}   
