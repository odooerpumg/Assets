# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Inventory Extension',
    'version': '1.0',
    'author': 'Myat Min Hein(M2h)',
    'category': 'Inventory',
    'sequence': 60,
    'summary': 'Inventory Assets',
    'description': "",
    'depends': ['product','stock','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
