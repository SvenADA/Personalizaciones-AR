# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInvoiceDownloadVouchersView(models.TransientModel):
	_name = "account.invoice.download.vouchers"
	_description = 'Descarga de comprobantes electrónicos'

	def action_download_vouchers(self):
		active_ids = self.env.context.get('active_ids')
		if not active_ids:
			return ''

		return {
			'name': 'Descargar comprobantes electrónicos',
			'res_model': 'account.invoice.download.vouchers',
			'view_mode': 'form',
			'view_id': self.env.ref('cr_electronic_invoice.account_invoice_download_vouchers_view').id,
			'context': self.env.context,
			'target': 'new',
			'type': 'ir.actions.act_window',
		}

	def download_vouchers(self):
		context = dict(self._context or {})
		active_ids = context.get('active_ids', []) or []

		return {
			'type': 'ir.actions.act_url',
			'url': '/web/binary/account_invoice_download_vouchers?ids=%s' % (active_ids),
			'target': 'self',
		}
