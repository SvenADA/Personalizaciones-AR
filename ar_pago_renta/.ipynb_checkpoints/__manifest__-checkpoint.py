# -*- coding: utf-8 -*-

{
    'name': 'Renta al salario',

    'summary': """ADA Robotics""",

    'description': """
        Modulo para realizar los pagos de renta mensualmente
    """,

    'Author': 'ADA Robotics',

    'website': 'adarobotics.com',

    'category': 'Human Resources',
    'version': '0.1',

    'depends': ['hr_contract', 'hr_payroll'],

    'data': [
        'views/payslip_view.xml',
        'views/contract_views.xml',
        'views/payslip_batch_view.xml',
        'views/payslip_tree_view.xml',
        #'security/security.xml',
        #'security/ir.model.access.csv',
    ],

    'demo': [
    ],
    'installable': True,
    'application': False,
}
