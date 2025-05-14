{
    'name': 'YZD Stock Tank',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Add capacity and current stock to locations for tank management',
    'description': """
        This module adds capacity and current stock fields to stock locations.
    """,
    'author': 'Your Name',
    'depends': ['base', 'mrp', 'planning', 'product', 'resource'],
    'data': [
        'views/stock_location_views.xml',  # فایل XML برای واسط کاربری
        'views/product_category_views.xml',  # فایل XML برای واسط کاربری
    ],
    'installable': True,
    'application': False,
}