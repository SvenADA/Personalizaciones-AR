# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DebitNoteWizard(models.TransientModel):
	_name = 'debit.note.wizard'
	_description = 'Wizard para creación de nota de débito'

	def _get_invoice_id(self):
		context = dict(self._context or {})
		active_id = context.get('active_id', False)
		return active_id

	reference_code_id = fields.Many2one(comodel_name="reference.code", string="Razón", required=True, )
	invoice_id = fields.Many2one(comodel_name="account.move", string="Documento de referencia", default=_get_invoice_id, required=False, )
	reference_reason = fields.Char(string="Detalle", required=False, size=179, copy=False)

	def create_debit_note(self):
		# Se elimina la validacion ya que se supone que si se pueden realizar una ND a una factura
		if self.invoice_id.move_type == 'out_invoice':
			if self.invoice_id.type_document == '02':
				# Se valida que cuando se hace una nota de debito tenga una nota de credito como referencia
				raise UserError('Error de Facturación Electrónica\nNo es permitido realizar una ND a otra ND')

		type_document_selection = self.env['type.document.selection'].search([('code', '=', '02')], limit=1)

		invoice_values = {
			'move_type': 'out_invoice',
			'partner_id': self.invoice_id.partner_id.id,
			'currency_id': self.invoice_id.currency_id.id,
			'journal_id': self.invoice_id.journal_id.id,
			'invoice_origin': self.invoice_id.name,
			'type_document_selection': type_document_selection.id,
			'payment_methods_id': self.invoice_id.payment_methods_id.id,
			'activity_type': self.invoice_id.activity_type.id,
			'fiscal_position_id': self.invoice_id.fiscal_position_id.id,
			'ref': str(self.invoice_id.name) + ': '+self.reference_reason[:179],
		}

		debit_note = self.create_invoice(invoice_values)

		invoce_lines = list()
		for line in self.invoice_id.invoice_line_ids:
			dict_line = {
				'move_id': debit_note.id,
				'product_id': line.product_id,
				'account_id': line.account_id,
				'name': line.name,
				'quantity': line.quantity,
				'price_unit': line.price_unit,
				'product_uom_id': line.product_uom_id,
				'discount': line.discount,
				'tax_ids': [[6, False, line.tax_ids.ids]],
			}
			format_line = [0, False, dict_line]
			invoce_lines.append(format_line)

		self.write_invoice_lines(debit_note, invoce_lines)

		reference_document = debit_note.reference_document_ids.create({
			'move_id': debit_note.id,
			'invoice_id': self.invoice_id.id,
			'reference_code_id': self.reference_code_id.id,
			'reference_reason': self.reference_reason[:179],
		})
		reference_document._type_reference_document()

		action = {
			'name': 'Nota de Débito',
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'view_mode': 'form',
			'res_id': debit_note.id,
		}
		return action

	def create_invoice(self, values):
		inv = self.env['account.move'].create(values)
		return inv

	def write_invoice_lines(self, debit_note, lines_values):
		return debit_note.write({'invoice_line_ids': lines_values})