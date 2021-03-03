# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Asset Extension',
    'version': '1.0',
    'author': 'Myat Min Hein(M2h)',
    'category': 'Asset',
    'sequence': 60,
    'summary': 'Assets',
    'description': "",
    'depends': ['product','stock','base','hr','fl_auth_signup'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/asset_request_view.xml',
        'views/asset_return_view.xml',
        'views/hr_employee_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
