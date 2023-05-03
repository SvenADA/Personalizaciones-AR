# -*- coding: utf-8 -*-

{
    'name': "Solicitud de Admision",
    'summary': "Modulo para el estudio de la solicitud de admision",
    'author': 'ADA Robotics',
    'website': 'adarobotics.com',
    'category':'Ventas',
    'version':'1.0.0',
    'depends':['base', 'mail', 'crm', 'helpdesk', 'project', 'documents', 'website'],
    'data': [
        'views/solicitud_view.xml',
        'views/solicitudAdmision_view.xml',
        'views/mail_message_custom.xml',
        'security/ir.model.access.csv',
        'data/template_email_form.xml',
        'views/request_form.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}