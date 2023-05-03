# -*- coding: utf-8 -*-

{
	'name': 'Provincias, cantones y distritos de Costa Rica',
	'version': '07.12.21',
	'author': 'DelfixCR',
	'license': 'OPL-1',
	'website': 'https://www.delfixcr.com',
	'category': 'Account',
	'description':
		'''
		Carga de datos de provincias, cantones y distritos
		''',
	'depends': [
		'base',
		'contacts',
	],
	'data': [
		'views/country_codes_views.xml',
		'data/res.country.county.csv',
		'data/res.country.state.csv',
		'data/res.country.district.csv',
		'data/res.country.neighborhood.csv',
		'security/ir.model.access.csv',
	],
	'installable': True,
}
