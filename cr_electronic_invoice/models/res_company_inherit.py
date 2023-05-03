# -*- coding: utf-8 -*-

import json
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from . import standard_tools
from OpenSSL import crypto
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class CompanyElectronic(models.Model):
	_name = 'res.company'
	_inherit = ['res.company', 'mail.thread']

	commercial_name = fields.Char(string="Nombre comercial", required=False, )
	phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506", help="Sin espacios ni guiones")
	fax = fields.Char(string="Fax", required=False, help="Sin espacios ni guiones")
	fax_code = fields.Char(string="Código de Fax", size=3, default="506", required=False, )
	signature = fields.Binary(string="Llave Criptográfica", )
	identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificacion", required=False, )
	district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=False, )
	county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=False, )
	neighborhood_id = fields.Many2one(comodel_name="res.country.neighborhood", string="Barrio", required=False, )
	api_key = fields.Char(string="Api Key", required=False, )
	frm_ws_identificador = fields.Char(string="Usuario", required=False, )
	frm_ws_password = fields.Char(string="Password", required=False, )
	frm_ws_ambiente = fields.Selection(selection=[
		('disabled', 'Deshabilitado'),
		('stag', 'Pruebas'),
		('prod', 'Producción'),
	], string="Ambiente", required=True, default='disabled',
		help='*Deshabilitado: No se envían Facturas a MH \n '
		     '*Pruebas: Se envían Facturas a MH pero no tiene validez para fines tributarios \n '
		     '*Producción: Se envían Facturas a MH y tiene validez para fines tributarios'
	)
	frm_pin = fields.Char(string="Pin", required=False, help='Correspondiente al certificado (Llave Criptográfica)')
	activated = fields.Boolean(compute="_verify_activation", string="Estado cliente Activo Inactivo", default=False)
	state = fields.Selection(string="Estado", selection=[
		('active', 'Activo'),
		('inactive', 'Inactivo'),
	], required=False, default='inactive')
	master_api_key = fields.Char(string="Api Key Master", required=False, help="Llave Maestra para generar tokens y realizar funciones de mantenimiento", )
	template_email_fe = fields.Many2one(comodel_name="mail.template", string="Plantilla de Correo Electronico Facturas", required=False)
	template_email_voucher = fields.Many2one(comodel_name="mail.template", string="Plantilla de Correo Electronico Comprobantes", required=False)
	report_invoice = fields.Many2one(comodel_name="ir.actions.report", string="Informe de facturas", )
	currency_used = fields.Boolean(string="Utilizar tasas de cambio", help="""*Utiliza tasas de cambio: la moneda CRC = 1 y USD = 0.001724
	*No utiliza tasas de cambio: la moneda CRC = 580 y USD = 1""", default=True)
	activity_type = fields.Many2one(comodel_name="activity.code", string="Actividad económica por defecto", required=False, copy=False, )
	health_service = fields.Boolean(string="Servicio de salud", )
	iva_condition_id = fields.Many2one(comodel_name="iva.condition", string="Condición del IVA por defecto", required=False)
	activity_types = fields.Many2many(comodel_name="activity.code", string="Actividades económicas", help="Se utilizan para realizar un dominio en el campo actividad económica en facturas, mostrando solo las seleccionadas")
	validate_pdf = fields.Boolean(string="Validar PDF adjunto", help="Válida en facturas de proveedor que el comprobante electrónico tenga su respectivo documento pdf adjunto a la factura")
	tax_return_iva = fields.Many2one(comodel_name="account.tax", string="Impuesto Devolución del IVA 4%", required=False, copy=False, help='Se utiliza cuando la compañía es de salud, vende servicios y el pago es realizado con Tarjeta.')
	special_tags_lines = fields.One2many(comodel_name="fe.special.tags.company.line", inverse_name="company_id", string="Líneas de etiquetas adicionales XML", required=False, )
	expiration_date_p12 = fields.Date(string="Fecha de expiración de Llave Criptográfica", required=False, compute="_compute_expiration_date_p12", store=True)
	product_id_electronic_voucher = fields.Many2one(comodel_name="product.product", string="Producto por defecto", required=False, copy=False, help="Se utilizará para la creación de factura de proveedor desde Comprobantes Electrónicos, donde las líneas de factura tendrán este producto por defecto.")
	show_cabys = fields.Boolean(string='Mostrar Cabys', required=False, help='Muestra en el reporte de factura y ventas el código cabys de cada producto')
	show_currency_rate = fields.Boolean(string='Mostrar tipo de cambio', required=False, help='Muestra en el reporte de factura el tipo de cambio')
	invoice_attachment_ids = fields.One2many(comodel_name="electronic.invoice.email.attachment.line", inverse_name="company_attachment_id", string="Adjuntos", required=False, help="Documentos que serán enviados por correo electrónico junto a los archivos de la factura electrónica")

	@api.depends('api_key')
	def _verify_activation(self):
		for company in self:
			if company.api_key:
				company.activated = True
			else:
				company.activated = False

	def get_environment_cyberfuel(self):
		ambiente = 'disabled'
		if self.frm_ws_ambiente == 'prod':
			ambiente = 'cHJvZA=='
		if self.frm_ws_ambiente == 'stag':
			ambiente = 'c3RhZw=='
		return ambiente

	def to_register_client(self):
		for rec in self:
			ambiente = rec.get_environment_cyberfuel()
			bytes_iden = base64.b64encode(rec.frm_ws_identificador.encode('utf-8'))
			bytes_pass = base64.b64encode(rec.frm_ws_password.encode('utf-8'))

			payload = {
				'api_key': rec.master_api_key,
				'frm_tipo_id': rec.identification_id.code,
				'frm_number_id': rec.vat,
				'frm_email': rec.email,
				'frm_nombre': rec.name,
				'frm_ws_ambiente': ambiente,
				'frm_ws_identificador': bytes_iden.decode('utf-8'),
				'frm_ws_password': bytes_pass.decode('utf-8'),
				'frm_crt': rec.signature.decode('utf-8'),
				'frm_pin': rec.frm_pin,
				'frm_callback_url': 'https://www.sudominio.com/repuesta.php?api_key=@@api_key@@',
			}
			headers = {}
			response_document = requests.post('https://www.comprobanteselectronicoscr.com/api/client.php?action=add_client', headers=headers, data=json.dumps(payload))

			values = json.loads(str(response_document._content, 'utf-8'))

			if values.get('token', False):
				rec.api_key = values.get('token', False)
				rec.state = 'active'
				return {
					'type': 'ir.actions.client',
					'tag': 'display_notification',
					'params': {
						'title': 'Cyberfuel',
						'message': 'Cliente registrado con éxito',
						'sticky': False,
					}
				}
			else:
				_logger.error(str(response_document._content, 'utf-8'))
				raise UserError("Error : " + str(values))

	def to_update_crt(self):
		for rec in self:
			ambiente = rec.get_environment_cyberfuel()

			payload = {
				'api_key': rec.api_key,
				'frm_ws_ambiente': ambiente,
				'frm_crt': rec.signature.decode('utf-8'),
				'frm_pin': rec.frm_pin,
			}
			headers = {}
			response_document = requests.post('https://www.comprobanteselectronicoscr.com/api/client.php?action=update_crt', headers=headers, data=json.dumps(payload))
			response_content = json.loads(str(response_document._content, 'utf-8'))

			if response_content.get('status') != 1:
				_logger.error(str(response_document._content, 'utf-8'))
				raise UserError("Se produjo un error desconocido")

			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': 'Cyberfuel',
					'message': 'Certificado actualizado con éxito',
					'sticky': False,
				}
			}

	def to_update_user(self):
		for rec in self:
			ambiente = rec.get_environment_cyberfuel()

			bytes_iden = base64.b64encode(rec.frm_ws_identificador.encode('utf-8'))
			bytes_pass = base64.b64encode(rec.frm_ws_password.encode('utf-8'))

			payload = {
				'api_key': rec.api_key,
				'frm_ws_ambiente': ambiente,
				'frm_usuario': bytes_iden.decode('utf-8'),
				'frm_ws_password': bytes_pass.decode('utf-8'),
				'frm_callback_url': 'https://www.sudominio.com/repuesta.php?api_key=@@api_key@@',
			}
			headers = {}
			response_document = requests.post('https://www.comprobanteselectronicoscr.com/api/client.php?action=update_user', headers=headers, data=json.dumps(payload))
			response_content = json.loads(str(response_document._content, 'utf-8'))

			if response_content.get('status') != 1:
				_logger.error(str(response_document._content, 'utf-8'))
				raise UserError("Se produjo un error desconocido")

			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': 'Cyberfuel',
					'message': 'Usuario actualizado con éxito',
					'sticky': False,
				}
			}

	def to_disable_client(self):
		for rec in self:
			ambiente = rec.get_environment_cyberfuel()

			bytes_iden = base64.b64encode(rec.frm_ws_identificador.encode('utf-8'))
			bytes_pass = base64.b64encode(rec.frm_ws_password.encode('utf-8'))

			payload = {
				'api_key': rec.master_api_key,
				'frm_tipo_id': rec.identification_id.code,
				'frm_number_id': rec.vat,
				'frm_email': rec.email,
				'frm_nombre': rec.name,
				'frm_ws_ambiente': ambiente,
				'frm_ws_identificador': bytes_iden.decode('utf-8'),
				'frm_ws_password': bytes_pass.decode('utf-8'),
				'frm_crt': rec.signature.decode('utf-8'),
				'frm_pin': rec.frm_pin,
			}
			headers = {}
			response_document = requests.post('https://www.comprobanteselectronicoscr.com/api/client.php?action=inactive_client', headers=headers, data=json.dumps(payload))
			response_content = json.loads(str(response_document._content, 'utf-8'))

			if response_content.get('status') != 1:
				_logger.error(str(response_document._content, 'utf-8'))
				raise UserError("Se produjo un error desconocido")

			rec.state = 'inactive'
			rec.api_key = False

			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': 'Cyberfuel',
					'message': 'Cliente inactivado con éxito',
					'sticky': False,
				}
			}

	# Se extrae las configuraciones del pos
	def get_config(self):
		config = self.env['config.electronic.invoice'].search([('id', '=', 1)], limit=1)
		return config

	@api.depends('signature', 'frm_pin')
	def _compute_expiration_date_p12(self):
		for company_id in self:
			expiration_date = company_id.get_expiration_date_p12()
			company_id.expiration_date_p12 = expiration_date

	def get_expiration_date_p12(self):
		if self.signature and self.frm_pin:
			try:
				if type(self.signature) is str:
					signature = self.signature.encode('utf-8')
				else:
					signature = self.signature
				p12 = crypto.load_pkcs12(base64.decodebytes(signature), self.frm_pin.encode('utf-8'))
				certificate = p12.get_certificate()
				expiration_date = datetime.strptime(certificate.get_notAfter().decode("utf-8"), "%Y%m%d%H%M%SZ").date()
				return expiration_date
			except:
				return False
		else:
			return False

	def _check_expiration_date_p12(self):
		res_company_ids = self.env['res.company'].search([
			('frm_ws_ambiente', '!=', 'disabled'),
		])
		for company_id in res_company_ids:
			if company_id.signature:
				expiration_date = company_id.get_expiration_date_p12()
				now_date_plus_two_months = (datetime.now() + timedelta(days=60)).date()

				if company_id.expiration_date_p12 != expiration_date:
					company_id.expiration_date_p12 = expiration_date
				if company_id.expiration_date_p12 <= now_date_plus_two_months:
					email_template = self.env.ref('cr_electronic_invoice.template_expiration_date_p12', False)
					email_template.send_mail(company_id.id, raise_exception=False, force_send=True)

	def get_valid_phone(self):
		return standard_tools.get_valid_phone(self.phone, self.phone_code)

	def get_valid_fax(self):
		return standard_tools.get_valid_phone(self.fax, self.fax_code)

	def write(self, vals):
		superr = super(CompanyElectronic, self).write(vals)
		for panert in self:
			if panert.phone_code:
				message = standard_tools.validate_phone_code(panert.phone_code)
				if message:
					raise UserError(message)

			if panert.phone:
				message = standard_tools.validate_phone(panert.phone)
				if message:
					raise UserError(message)

			if panert.fax_code:
				message = standard_tools.validate_fax_code(panert.fax_code)
				if message:
					raise UserError(message)

			if panert.fax:
				message = standard_tools.validate_fax(panert.fax)
				if message:
					raise UserError(message)

			if panert.email:
				message = standard_tools.validate_email(panert.email)
				if message:
					raise UserError(message)

			cedula = panert.vat
			if cedula and panert.identification_id:
				message = standard_tools.validate_identification(cedula, str(panert.identification_id.code))
				if message:
					raise UserError(message)
		return superr
