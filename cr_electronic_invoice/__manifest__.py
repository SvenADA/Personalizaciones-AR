# -*- coding: utf-8 -*-
##############################################################################
#	Odoo Proprietary License v1.0
#	Copyright (c) 2023 Facturación electrónica All Rights Reserved.
##############################################################################
{
	'name': 'Facturación Electrónica CR',
	'version': '24.02.23',
	'author': 'FE_CR',
	'license': 'OPL-1',
	'support': 'support@mail.com',
	'website': 'https://www.website.com',
	'category': 'Account',
	'description':
		'''
		Facturación Electronica de Costa Rica.
		''',
	'depends': [
		'base',
		'account',
		'uom',
		'product',
		'contacts',
		'l10n_cr',
		'l10n_cr_country_codes',
		'mail',
		'sale',
	],
	'data': [
		'security/res_groups.xml',
		'security/ir.model.access.csv',

		'views/data_models_views.xml',
		'views/account_journal_views.xml',
		'views/account_tax_inherit_views.xml',
		'views/account_move_reversal_views.xml',
		'views/res_company_inherit_views.xml',
		'views/res_partner_inherit_views.xml',
		'views/account_move_inherit_views.xml',
		'views/config_electronic_invoice_views.xml',
		'views/electronic_voucher_supplier_views.xml',
		'views/purchase_invoice_wizard_views.xml',
		'views/product_template_view_inherit.xml',
		'views/debit_note_wizard_views.xml',
		'views/reference_document_line_views.xml',
		'views/fe_special_tags_line_views.xml',
		'views/res_partner_result_mh_wizard_views.xml',
		'views/res_partner_result_mh_exoneration_wizard_views.xml',
		'views/account_fiscal_position_inherit_views.xml',
		'views/product_category_view_inherit.xml',
		'views/product_result_cabys_wizard_views.xml',

		'reports/external_loyout_standard_replace.xml',
		'reports/external_layout_bold_replace.xml',
		'reports/external_layout_striped_replace.xml',
		'reports/external_layout_boxed_replace.xml',
		'reports/report_invoice_replace.xml',
		'reports/report_saleorder_document.xml',
		#'reports/report_invoice_document_inherit_sale.xml',

		'data/mail_template_voucher_supplier.xml',
		'data/mail_template_expiration_date_p12.xml',
		'data/ir_cron.xml',
		'data/code.type.product.csv',
		'data/identification.type.csv',
		'data/payment.methods.csv',
		'data/reference.code.csv',
		'data/sale.conditions.csv',
		'data/uom.uom.csv',
		'data/uom_uom.xml',
		'data/config_electronic_invoice.xml',
		'data/invoice.tax.code.rate.csv',
		'data/invoice.tax.type.csv',
		'data/type.other.charges.csv',
		'data/type.reference.document.csv',
		'data/exoneration_type.xml',
		'data/iva.condition.csv',
		'data/account_tax.xml',
		'data/type.document.selection.csv',
		'data/account.payment.term.csv',
	],
	'installable': True,
}
