# -*- coding: utf-8 -*-
{
    'name': "just_todo",

    'summary': """
        workflow todo task. """,

    'description': """
        workflow todo task. 
    """,

    'author': "justzxw",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tools',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'mail',
    ],

    # always loaded
    'data': [
        'data/stages.xml',
        'security/ir.model.access.csv',
        'views/todo_activity.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
	      'just_todo/static/src/scss/style.scss',
        ],
    },
    
	'license': 'LGPL-3',
}