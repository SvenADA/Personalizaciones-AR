# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json
import requests
from datetime import datetime
from odoo.exceptions import UserError, Warning, ValidationError


class ExonerationTaxElectronicInvoice(models.Model):
	_name = "exoneration.tax.electronic.invoice"
	_description = "Documento de Exoneración"

	name = fields.Char(string="Nombre", required=False, )
	document_type_id = fields.Many2one(comodel_name="exoneration.type", string="Tipo de Documento", required=False, )
	institution_name = fields.Char(string="Nombre de institución", required=True, size=160)
	document_number = fields.Char(string="Número de documento", required=True, size=40)
	date_issue = fields.Date(string="Fecha de emisión", required=True, )
	time_issue = fields.Char(string="Hora de emisión", required=True, default="00:00:00")
	purchase_percentage = fields.Integer(string="Porcentaje de exoneración", required=True, default=13, help="""
	Las exoneraciones comúnmente tienen 13 puntos de exoneración.

	Ejemplos:

	Puntos = 1 ---- Impuesto a exonerar = 13% ---- Impuesto aplicar = 12%
	Puntos = 2 ---- Impuesto a exonerar = 13% ---- Impuesto aplicar = 11%
	Puntos = 4 ---- Impuesto a exonerar = 13% ---- Impuesto aplicar = 9%
	Puntos = 13 ---- Impuesto a exonerar = 13% ---- Impuesto aplicar = 0%

	Ejemplos con tarifas:

	Puntos = 13 ---- Impuesto a exonerar = Tarifa Reducida 1% ---- Impuesto aplicar = 0%
	Puntos = 13 ---- Impuesto a exonerar = Tarifa Reducida 2% ---- Impuesto aplicar = 0%
	Puntos = 13 ---- Impuesto a exonerar = Tarifa Reducida 4% ---- Impuesto aplicar = 0%

	Si se desea facturar a una universidad u organización exonerada por ley, se debe utilizar la tarifa que corresponda, \npor lo que no necesitan documento de exoneración, por lo tanto el campo “Documento de Exoneración” debe ser vacío. \nSin embargo si desea facturar al 0% si es necesario el documento de Exoneración.
	""")
	default_time_issue = fields.Boolean(string="Hora por defecto", compute="_compute_default_time_issue", store=False)
	due_date = fields.Date(string="Fecha de vencimiento", required=False, help="Si se asigna se comprobará su fecha de vencimiento al validar la factura")
	validate_cabys = fields.Boolean(string='Validar cabys', required=False, help="Al validar la factura se busca que los productos estén dentro del dominio de cabys de la exoneración")
	cabys_line_ids = fields.One2many('exoneration.cabys.line', 'exoneration_id', string='Cabys permitidos')
	partner_id = fields.Many2one('res.partner', string='Contacto', help="Cliente relacionado a la exoneración")

	@api.depends('document_type_id')
	def _compute_default_time_issue(self):
		for rec in self:
			if rec.document_type_id and rec.document_type_id.code == '04':
				rec.time_issue = '00:00:00'
				rec.default_time_issue = True
			else:
				rec.default_time_issue = False

	@api.constrains('time_issue')
	def validate_time_issue(self):
		for record in self:
			error = False
			if len(str(record.time_issue)) != 8:
				error = True
			elif not (str(record.time_issue)[0:2].isdigit() and str(record.time_issue)[3:5].isdigit() and str(record.time_issue)[6:8].isdigit()):
				error = True
			if error:
				raise ValidationError("Se requiere el siguiente formato. Ej: 10:30:00")

	# https://api.hacienda.go.cr/fe/ex?codigo = 848129
	@api.constrains('purchase_percentage')
	def _check_purchase_percentage(self):
		if self.purchase_percentage:
			if not 0 <= self.purchase_percentage <= 13:
				raise ValidationError("Por favor ingrese un porcentaje de exoneración igual o menor a 13")

	# AL-00125455-19, AL-00252712-21, AL-00120499-21
	def consult_exoneration(self):
		response = self._consult_exo_code(self.document_number)
		return self.exoneration_wizard(response)

	def exoneration_wizard(self, response):
		if response:
			action = self.sudo().env.ref('cr_electronic_invoice.action_res_partner_result_mh_exoneration_wizard').read()[0]
			partner_id = self.env['res.partner'].search([('ref', '=', response.get('identificacion'))], limit=1)
			date_issue = datetime.strptime(response.get('fechaEmision'), "%Y-%m-%dT%H:%M:%S")
			due_date = datetime.strptime(response.get('fechaVencimiento'), "%Y-%m-%dT%H:%M:%S")
			cabys_line_ids = [(0, 0, {'code': cabys}) for cabys in response.get('cabys', [])]

			result_wizard = self.env['res.partner.result.mh.exoneration.wizard'].create({
				'res_partner_id': (partner_id and partner_id.id) or False,
				'name': response.get('numeroDocumento'),
				'ref': response.get('identificacion'),
				'date_issue': date_issue.date(),
				'due_date': due_date.date(),
				'document_type': response.get('tipoDocumento').get('descripcion'),
				'name_institution': response.get('nombreInstitucion'),
				'exoneration_percentage': response.get('porcentajeExoneracion') or 13,
				'cabys_line_ids': cabys_line_ids,
				'code_cfia': str(response.get('codigoProyectoCFIA', '')),
			})

			action.update({
				'res_id': result_wizard.id
			})
			return action

	def _consult_exo_code(self, document_number):
		url = "https://api.hacienda.go.cr/fe/ex?autorizacion="
		if document_number:
			url += str(document_number)
			response_document = requests.get(url, verify=False)
			response_content = json.loads(str(response_document._content, 'utf-8'))
			if response_document.status_code == 200:
				return response_content
			elif response_document.status_code == 404:
				raise UserError('Documento no encontrado en la base de datos de MH: ' + str(document_number))
			elif response_document.status_code == 400:
				raise UserError('Formato incorrecto de Número de documento: ' + str(document_number) + '\nSolo documentos con formato: AL-00125155-19 se pueden consultar')
			else:
				raise UserError('Error desconocido')
		else:
			return False


class ExonerationCabysLine(models.Model):
	_name = "exoneration.cabys.line"
	_description = "Lineas de cabys de exoneracion"

	exoneration_id = fields.Many2one('exoneration.tax.electronic.invoice', string='Documento de Exoneración', ondelete='cascade', index=True)
	code = fields.Char(string='Código', required=False)
	product_id = fields.Many2one(comodel_name="product.product", string="Producto encontrado", required=False, compute="_compute_product_id")
	category_id = fields.Many2one(comodel_name="product.category", string="Categoría encontrada", required=False, compute="_compute_category_id")

	def _compute_product_id(self):
		for rec in self:
			if rec.code:
				product_id = self.env['product.product'].search_read([('cabys_code', '=', rec.code)], fields=['id'], limit=1)
				if product_id:
					rec.product_id = product_id[0]['id']
				else:
					rec.product_id = False
			else:
				rec.product_id = False

	def _compute_category_id(self):
		for rec in self:
			if rec.code:
				category_id = self.env['product.category'].search_read([('cabys_code', '=', rec.code)], fields=['id'], limit=1)
				if category_id:
					rec.category_id = category_id[0]['id']
				else:
					rec.category_id = False
			else:
				rec.category_id = False


class AccountFiscalPositionInherit(models.Model):
	_name = 'account.fiscal.position'
	_inherit = ['account.fiscal.position', 'mail.thread']


# Se habilita el oe_chatter


class AccountFiscalPositionTaxInherit(models.Model):
	_inherit = "account.fiscal.position.tax"

	exoneration = fields.Many2one(comodel_name="exoneration.tax.electronic.invoice", string="Documento de Exoneración", required=False, )

	@api.constrains('exoneration', 'tax_dest_id', 'tax_src_id')
	def _check_exoneration(self):
		for line in self:
			if line.exoneration:
				applied_tax = round(line.tax_src_id.amount - line.exoneration.purchase_percentage, 2)
				if applied_tax < 0:
					applied_tax = 0
				if line.tax_dest_id.amount != applied_tax:
					raise ValidationError("El porcentaje de exoneración no concuerda con el 'impuesto para aplicar'. "
					                      "\n\nDe acuerdo al porcentaje de exoneración, el “impuestos para aplicar” debería ser: " + str(applied_tax) +
					                      "\n\nPor favor verifique el porcentaje de exoneración o el impuesto. "
					                      "\n\nNota: el monto sugerido puede ser incorrecto, si el monto de exoneración o el impuesto a sustituir son incorrectos.")
