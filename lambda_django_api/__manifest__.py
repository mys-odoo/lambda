# -*- coding: utf-8 -*-
{
    'name': "Lambda Django APIs",

    'summary': "Lambda Django APIs",

    'description': "Create SO from Django, Update SO, Initial Attribute Data, Update Master BOM",

    'author': "Syncoria",
    'website': "http://www.syncoria.com",

    'category': 'Sales',
    'version': '0.1',

    'depends': ['base', 'sale', 'product', 'syncoria_api_authentication'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/sale.xml',
        'views/product.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    
}   
