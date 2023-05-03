# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInvoiceSendElectronicInvoice(models.TransientModel):
	_inherit = "account.invoice.send"

	@api.onchange('template_id')
	def onchange_template_id(self):
		# Antes en action_invoice_sent
		# Se hereda dede onchange_template_id para evitar que attachment_ids y partner_ids sean remplazados
		res = super(AccountInvoiceSendElectronicInvoice, self).onchange_template_id()

		for wizard in self:

			inv = self.env['account.move'].browse(wizard.res_id)

			mails = inv.partner_id._get_emails().split(',')
			model_partner = inv.env['res.partner']

			# Forma en que trabaja el mail.compose.message
			# Todo ver como quitar los partner creados con email
			partner_ids = list()
			for mail in mails:
				# El split devuelve [''] cuando no hay correos
				if mail:
					partner = model_partner.find_or_create(mail)
					partner_ids.append(partner.id)

			attachments_ids = inv._get_attachments_ids(inv)

			wizard.update({
				'attachment_ids': [(6, 0, attachments_ids)],
				'partner_ids': [(6, 0, partner_ids)],
			})
		return res
