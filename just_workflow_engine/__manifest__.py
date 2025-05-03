# -*- coding: utf-8 -*-
##############################################################################
{
    "name": "Business driven workflow framework",
    "version": "17.2.0",
    'license': 'OPL-1',
    "depends": ["web","just_todo","just_workflow_bpmn"],
    "author": "justzxw",
    "category": "Tools",
    "description": """
       A Business Driven Workflow Tool.
    """,
    "data": [
        'secureity/ir.model.access.csv',
        'views/workflow.xml',
        'wizard/wizard_workflow.xml',
        #'views/Workflow_test.xml'
    ],
    
    'installable': True,
    'active': True,
    'auto_install': True,
    'images': [
        'static/description/theme.jpg',
    ],

    "price": 4000.0,
    "currency": "USD",
}
