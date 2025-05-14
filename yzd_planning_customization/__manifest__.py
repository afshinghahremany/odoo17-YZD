{
    'name': 'Production Planning Customization',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Customization for Production Planning',
    'description': """
        Customization for Production Planning including:
        - Production Planning Model
        - Tree and Form Views
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'planning',
        'mrp',
        'mail',
        'stock',
        'purchase_request',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/transport_planning_sequence.xml',
        'views/production_planning_views.xml',
        'views/planning_config_settings_views.xml',
        'views/mrp_bom_views.xml',
        'views/product_template_views.xml',
        'views/production_planning_return_wizard_views.xml',
        'views/transport_planning_views.xml',
        'views/product_category_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'yzd_planning_customization/static/src/css/style.css',
        ],
    },
}
