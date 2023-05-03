# -*- coding: utf-8 -*-
{
    'name': "Website Product Multi UOM",

    'summary': """Select the Product's UOM before adding to Cart""",

    'description': """This add-on will integrate a functionality in the "eCommerce" application to select the unit of 
    measurement for the product before adding it to the cart""",

    'author': 'ErpMstar Solutions',
    'category': 'Website',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    # always loaded
    'data': [
        'views/templates.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            '/website_product_multi_uom/static/src/js/uom.js',
        ]
    },
    'images': [
        'static/description/uom_dozen.png',
    ],
    'installable': True,
    'website': '',
    'auto_install': False,
    'price': 30,
    'currency': 'EUR',
    'live_test_url': 'https://www.youtube.com/watch?v=p1mWrkv_P3U'
}
