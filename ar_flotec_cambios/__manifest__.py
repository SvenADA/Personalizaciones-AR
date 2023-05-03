# -*- coding: utf-8 -*-

{
    'name': 'Colaboradores y contratos',

    'summary': """ADA Robotics""",

    'description': """
        Modulo que cambia atributos de modelos como contratos y empleados
    """,

    'Author': 'ADA Robotics',

    'website': 'adarobotics.com',

    'category': 'Human Resources',
    'version': '0.1',

    'depends': ['hr_contract', 'hr_payroll'],

    'data': [
        'views/contratos.xml',
        'views/empleados.xml',
        #'views/payslip_tree_view.xml',
        #'security/security.xml',
        #'security/ir.model.access.csv',
    ],

    'demo': [
    ],
    'installable': True,
    'application': False,
}
