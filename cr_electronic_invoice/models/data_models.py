# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import standard_tools
from datetime import datetime


class MailsElectronicInvoice(models.Model):
	_name = "mails.electronic.invoice"
	_description = 'Correo Electrónico Adicional'

	name = fields.Char(string="Correo adicional para FE", required=True)
	send_mail = fields.Boolean(string="Enviar", required=False, default=True, help="Si está marcado se envía el correo electrónico de FE a la dirección indicada")
	main_email = fields.Boolean(string="Principal", required=False, help="Si está marcado se muestra el correo en el reporte y xml de la FE")
	res_partner_id = fields.Many2one(comodel_name="res.partner", ondelete='cascade', index=True)


class IdentificationType(models.Model):
	_name = "identification.type"
	_description = 'Tipo de identificación'

	code = fields.Char(string="Código", required=False, )
	name = fields.Char(string="Nombre", required=False, )
	notes = fields.Text(string="Notas", required=False, )


class CodeTypeProduct(models.Model):
	_name = "code.type.product"
	_description = 'Tipo de código del producto'

	code = fields.Char(string="Código", required=False, )
	name = fields.Char(string="Nombre", required=False, )


class ExonerationType(models.Model):
	_name = "exoneration.type"
	_description = 'Tipos de exoneración'

	code = fields.Char(string="Código", required=False, )
	name = fields.Char(string="Nombre", required=False, )
	notes = fields.Text(string="Notas", required=False, )
	active = fields.Boolean(default=True, string="Activo", )


class IvaCondition(models.Model):
	_name = "iva.condition"
	_description = 'Condición del IVA'

	name = fields.Char(string="Nombre", required=False, )
	code = fields.Char(string="Código", required=False, size=2)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )


class TypeReferenceDocumentCode(models.Model):
	_name = "type.reference.document"
	_description = 'Tipo de documento de referencia'

	name = fields.Char(string="Nombre", required=False, )
	code = fields.Char(string="Código", required=False, size=2)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )


class ActivityCode(models.Model):
	_name = "activity.code"
	_description = 'Códigos de actividad'

	name = fields.Char(string="Nombre", required=False, )
	code = fields.Char(string="Código", required=False, size=6)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )

	@api.constrains('code')
	def _check_code(self):
		for rec in self:
			if len(rec.code) != 6:
				raise ValidationError("Por favor ingrese un código de 6 dígitos, si el código es de 5 dígitos agregue un 0 al lado izquierdo o verifique el código.")


class TypeOtherCharges(models.Model):
	_name = "type.other.charges"
	_description = 'Tipo de otros cargos'

	name = fields.Char(string="Nombre", required=False, )
	code = fields.Char(string="Código", required=False, size=2)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )


class InvoiceTaxType(models.Model):
	_name = "invoice.tax.type"
	_description = 'Tipo de impuesto'

	name = fields.Char(string="Nombre", required=False, )
	code = fields.Char(string="Código", required=False, size=2)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )


class InvoiceTaxCodeRate(models.Model):
	_name = "invoice.tax.code.rate"
	_description = 'Código de la tarifa del impuesto'

	name = fields.Char(string="Nombre", required=False, )
	rate = fields.Char(string="Tarifa", required=False, )
	code = fields.Char(string="Código", required=False, size=2)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )


class AccountPaymentTerm(models.Model):
	_inherit = "account.payment.term"

	sale_conditions_id = fields.Many2one(comodel_name="sale.conditions", string="Condiciones de venta", required=False)


class PaymentMethods(models.Model):
	_name = "payment.methods"
	_description = 'Método de pago'

	active = fields.Boolean(string="Activo", required=False, default=True)
	sequence = fields.Char(string="Secuencia", required=False, )
	name = fields.Char(string="Nombre", required=False, )
	notes = fields.Text(string="Notas", required=False, )


class SaleConditions(models.Model):
	_name = "sale.conditions"
	_description = 'Condición de venta'

	active = fields.Boolean(string="Activo", required=False, default=True)
	sequence = fields.Char(string="Secuencia", required=False, )
	name = fields.Char(string="Nombre", required=False, )
	notes = fields.Text(string="Notas", required=False, )


class ReferenceCode(models.Model):
	_name = "reference.code"
	_description = 'Código de referencia'

	active = fields.Boolean(string="Activo", required=False, default=True)
	code = fields.Char(string="Código", required=False, )
	name = fields.Char(string="Nombre", required=False, )


class ProductUom(models.Model):
	_inherit = "uom.uom"

	code = fields.Char(string="Código", required=False, help='Este código ya está establecido por el MH, por lo que debe buscar el código correcto relacionado a la unidad de medida.')


class ExternalDocument(models.Model):
	_name = "external.document"
	_description = 'Documento externo'

	is_electronic_invoice = fields.Boolean(string="Factura Electrónica", required=False, default=True, help="Se valida que el Número Electrónico sea de 50 dígitos")
	fname_electronic_voucher = fields.Char(string="Nombre de archivo", required=False, copy=False)
	electronic_voucher = fields.Binary(string="Comprobante electrónico", attachment=True)
	is_validate = fields.Boolean(string="Validada", required=False, default=False)
	number_electronic = fields.Char(string="Número del documento", required=False, copy=False, index=True, help='Número electrónico, Orden del ICE, Número de factura timbrada, etc.')
	date_invoice = fields.Datetime(string="Fecha de emisión", required=False, copy=False)
	date_issuance = fields.Char(string="Fecha de emisión formato", required=False, copy=False)

	_rec_name = "number_electronic"

	@api.constrains('number_electronic')
	def _check_number_electronic(self):
		for record in self:
			if record.is_electronic_invoice:
				if len(record.number_electronic) != 50:
					raise ValidationError('Error de Facturación Electrónica\n Ingrese un Número Electrónico de 50 digitos, tamaño actual: %s' % str(len(record.number_electronic)))

	@api.onchange('date_invoice')
	def onchange_date_invoice(self):
		if self.date_invoice and (not self.electronic_voucher):
			self.date_issuance = self.date_invoice.strftime("%Y-%m-%dT%H:%M:%S-06:00")

	@api.onchange('electronic_voucher')
	def _onchange_electronic_voucher(self):
		if self.electronic_voucher:
			root = standard_tools.xml_supplier_to_ET(self.electronic_voucher)
			if not root.findall('Clave'):
				return {'value': {'electronic_voucher': False}, 'warning': {'title': 'Atención', 'message': 'El archivo xml no contiene el nodo Clave. Por favor cargue un archivo con el formato correcto.'}}
			if not root.findall('FechaEmision'):
				return {'value': {'electronic_voucher': False}, 'warning': {'title': 'Atención', 'message': 'El archivo xml no contiene el nodo FechaEmision. Por favor cargue un archivo con el formato correcto.'}}
			self.number_electronic = root.findall('Clave')[0].text
			self.date_invoice = str(datetime.strptime(root.findall('FechaEmision')[0].text, "%Y-%m-%dT%H:%M:%S-06:00").date())
			self.date_issuance = root.findall('FechaEmision')[0].text

	def unlink(self):
		for record in self:
			if record.is_validate:
				raise ValidationError('El documento se encuentra ligado a una factura, no es permitido eliminarlo')
		return super(ExternalDocument, self).unlink()


class TypeDocument(models.Model):
	_name = "type.document.selection"
	_description = 'Tipo de documento'

	name = fields.Char(string="Nombre", required=False, )
	code = fields.Char(string="Código", required=False, size=2)
	active = fields.Boolean(string="Activo", default=True)
	notes = fields.Text(string="Nota", required=False, )


class ElectronicInvoiceEmailAttachmentLine(models.Model):
	_name = "electronic.invoice.email.attachment.line"
	_description = 'Adjuntos adicionales de email'

	# Linea de Factura
	invoice_attachment_id = fields.Many2one(comodel_name="account.move", string="Factura", required=False, ondelete='cascade', index=True)

	# Linea de Compannia
	company_attachment_id = fields.Many2one(comodel_name="res.company", string="Compañía", required=False, ondelete='cascade', index=True)

	fname_email_attachment = fields.Char(string="Nombre de archivo", required=False, copy=False)
	email_attachment = fields.Binary(string="Documento / Archivo", required=False, copy=False, attachment=True)

	_rec_name = "fname_email_attachment"
