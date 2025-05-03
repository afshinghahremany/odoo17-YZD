{
    'name': 'YZD Planning Customization',
    'version': '17.0.1.0.0',
    'summary': 'Custom planning slot filters to show only material resources',
    'depends': ['planning', 'resource'],
    'author': 'Your Company',
    'depends': ['yzd_stock_tank'],
    'category': 'Planning',
    'data': [
        'views/yzd_planning_slot_views.xml',
        'views/yzd_mrp_bom_views.xml',
        'views/yzd_mrp_settings_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
