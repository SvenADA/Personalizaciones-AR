# -*- coding: utf-8 -*-
{
    'name': "Test Send Email",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "Flash",
    'website': "https://www.flashodoo.com",
    'category': 'Custom',
    'version': '1.0',
    'depends': [
        'base',
        'mail',
        'contacts',
    ],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
}