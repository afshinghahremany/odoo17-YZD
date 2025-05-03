{
    'name': 'YZD Stock Tank',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Add capacity and current stock to locations for tank management',
    'description': """
        This module adds capacity and current stock fields to stock locations.
    """,
    'author': 'Your Name',
    'depends': ['base', 'stock'],  # وابستگی به ماژول‌های پایه و انبار
    'data': [
        'views/stock_location_views.xml',  # فایل XML برای واسط کاربری
    ],
    'installable': True,
    'application': False,
}