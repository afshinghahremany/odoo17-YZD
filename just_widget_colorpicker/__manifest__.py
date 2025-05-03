# -*- coding: utf-8 -*-
{
    "name": """Just Widget Colorpicker""",
    "summary": """Just Color Picker for From""",
    "category": "web",
    "images": ['static/description/icon.png'],
    "version": "17.0.10.06",
    "description": """
            ...
            <field name="arch" type="xml">
                <form string="View name">
                    ...
                    <field name="CharField" widget="justcolorpicker" type="simple/common/complex"/>
                    ...
                </form>
            </field>
            ...

    """,

    "author": "justzxw",
    "license": "LGPL-3",
    "support": "justsxl@sina.com",
    "price": 2.57,
    "currency": "USD",

    "depends": [
        "web"
    ],

    'assets': {
        'web.assets_backend': [
            'just_widget_colorpicker/static/src/css/color-picker.less',
            'just_widget_colorpicker/static/src/owl/*.*',
        ]
    },
    
    "installable": True,
    "auto_install": False,
    "application": False,
}

