# -*- coding: utf-8 -*-
##############################################################################
#	Odoo Proprietary License v1.0
#	Copyright (c) 2023 Facturación electrónica All Rights Reserved.
##############################################################################
{
	'name': 'FE Directo a MH',
	'version': '24.02.23',
	'author': 'FE_CR',
	'license': 'OPL-1',
	'support': 'support@mail.com',
	'website': 'https://www.website.com',
	'category': 'Account',
	'description':
		'''
		Facturación Electronica directa a MH de Costa Rica.
		''',
	'depends': [
		'base',
		'cr_electronic_invoice',
	],
	'data': [
		'security/ir.model.access.csv',
		'views/res_company_inherit_views.xml',
		'views/download_documents_sent_views.xml',
		'views/config_electronic_invoice_inherit_views.xml',
	],
	'installable': True,
}
