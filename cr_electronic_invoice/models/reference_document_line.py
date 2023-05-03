# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ReferenceDocumentLine(models.Model):
	_name = "reference.document.line"
	_description = 'Líneas de Documento de referencia'

	move_id = fields.Many2one(comodel_name="account.move", string="Factura", required=False, copy=False, ondelete='cascade', index=True, invisible=True)
	invoice_id = fields.Many2one(comodel_name="account.move", string="Documento", required=False, copy=False)
	type_reference_document_id = fields.Many2one(comodel_name="type.reference.document", string="Tipo de documento", required=False, copy=False, store=True, help='Tipo de documento seleccionado en el campo “Documento de referencia” o acción específica a realizar sobre el documento. Ej: Reemplaza factura rechazada por MH.')
	reference_code_id = fields.Many2one(comodel_name="reference.code", string="Razón", required=False, copy=False)
	reference_reason = fields.Char(string="Detalle", required=False, size=179, copy=False)
	external_document_id = fields.Many2one(comodel_name="external.document", copy=False, string="Documento Externo")

	@api.onchange('reference_code_id')
	def onchange_reference_code_id(self):
		if self.reference_code_id:
			self.reference_reason = self.reference_code_id.name

	@api.onchange('invoice_id')
	def _compute_type_reference_document(self):
		self._type_reference_document()

	def _type_reference_document(self):
		if self.invoice_id:
			self.type_reference_document_id = self.get_type_reference_document(self.invoice_id)

	def get_type_reference_document(self, invoice_id):
		if invoice_id:
			if invoice_id.type_document == '09':
				code = '12'
			elif invoice_id.type_document == '08':
				code = '15'
			else:
				code = invoice_id.type_document

			type_reference_document = self.env['type.reference.document'].search([('code', '=', code)], limit=1)
			return type_reference_document
		return False

	@api.constrains('invoice_id', 'external_document_id')
	def _check_document(self):
		for line in self:
			if line.invoice_id and line.external_document_id:
				raise ValidationError('No se permite más de un documento, elija el campo “Documento” o  “Documento externo”')