# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMoveReversalElectronicInvoice(models.TransientModel):
	_inherit = "account.move.reversal"

	@api.model
	def _get_invoice_id(self):
		context = dict(self._context or {})
		active_id = context.get('active_id', False)
		if active_id:
			return active_id
		return False

	reference_code_id = fields.Many2one(comodel_name="reference.code", string="Razón", required=False, )
	invoice_id = fields.Many2one(comodel_name="account.move", string="Documento de referencia", default=_get_invoice_id, required=False, )

	def _prepare_default_reversal(self, move):
		values = super(AccountMoveReversalElectronicInvoice, self)._prepare_default_reversal(move)

		if self.invoice_id and self.invoice_id.move_type == 'out_invoice':
			type_reference_document = self.env['reference.document.line'].get_type_reference_document(self.invoice_id)
			reference_document = {
				'invoice_id': self.invoice_id.id,
				'reference_code_id': self.reference_code_id.id,
				'reference_reason': self.reason[:179],
				'type_reference_document_id': type_reference_document.id,
			}

			values.update({
				'payment_methods_id': self.invoice_id.payment_methods_id.id,
				'invoice_payment_term_id': self.invoice_id.invoice_payment_term_id.id,
				'activity_type': self.invoice_id.activity_type.id,
				'reference_document_ids': [(0, 0, reference_document)],
			})
		return values
