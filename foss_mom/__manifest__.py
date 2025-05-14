# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Minutes of Meeting",
    'price': 130.0,
    'currency': 'USD',
    'version': '17.0.0.0.0',
    'summary': """ Minutes of Meeting """,
    'author': 'FOSS INFOTECH PVT LTD',
    'license': 'Other proprietary',
    'category': 'Productivity',
    'website': "http://www.fossinfotech.com",
    'description': """
    """,
    'depends': ['base','calendar','project','survey'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'views/mom_views.xml',
        'report/layout.xml',
        'report/reports.xml',
        'report/mom_report_template.xml',
        'data/foss_mom_email_template.xml',
        'views/meeting_views.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/index.html',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
