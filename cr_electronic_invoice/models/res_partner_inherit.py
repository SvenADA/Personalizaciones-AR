# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from . import standard_tools
import json
import requests
from odoo.exceptions import UserError, Warning, ValidationError
from datetime import datetime


class PartnerElectronic(models.Model):
	_inherit = "res.partner"

	def _get_default_country_cr(self):
		return self.env.ref('base.cr', False)

	commercial_name = fields.Char(string="Nombre comercial", required=False, )
	phone_code = fields.Char(string="Código de teléfono", size=3, required=False, default="506", help="Sin espacios ni guiones")
	fax = fields.Char(string="Fax", required=False, )
	fax_code = fields.Char(string="Código de Fax", size=3, required=False, default="506", help="Sin espacios ni guiones")
	state_id = fields.Many2one(comodel_name="res.country.state", string="Provincia", required=False, )
	district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=False, )
	county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=False, )
	neighborhood_id = fields.Many2one(comodel_name="res.country.neighborhood", string="Barrios", required=False, )
	identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificación", required=False, )
	payment_methods_id = fields.Many2one(comodel_name="payment.methods", string="Método de Pago", required=False, )
	emails_ids = fields.One2many(comodel_name="mails.electronic.invoice", inverse_name="res_partner_id", string='Correos electrónicos adicionales para FE')
	export_invoice = fields.Boolean(string="Factura de exportación", copy=False)
	purchase_invoice = fields.Boolean(string="Factura de compra", copy=False)
	activity_types = fields.Many2many(comodel_name="activity.code", string="Actividades económicas Proveedor", help="Se utilizan para realizar un dominio en el campo actividad económica en facturas, mostrando solo las seleccionadas")
	activity_type = fields.Many2one(comodel_name="activity.code", string="Actividad económica por defecto", required=False, copy=False, )
	is_special_taxpayer = fields.Boolean(string="Contribuyente especial", )
	special_tags_lines = fields.One2many(comodel_name="fe.special.tags.partner.line", inverse_name="partner_id", string="Líneas de etiquetas adicionales XML", required=False, )
	product_id_electronic_voucher = fields.Many2one(comodel_name="product.product", string="Producto por defecto", required=False, copy=False, help="Se utilizará para la creación de factura de proveedor desde Comprobantes Electrónicos, donde las líneas de factura tendrán este producto por defecto.")
	country_id = fields.Many2one(default=_get_default_country_cr)
	zip = fields.Char(compute="_compute_zip", store=True)
	electronic_voucher_create_invoice = fields.Boolean(string='Crear factura de proveerdor', required=False, help="Crear factura de proveedor al cargar el comprobante electrónico desde el email")
	not_send_mail_fe = fields.Boolean(string='No enviar correo FE', required=False, help="Deshabilita el envió automático de la factura y los XML por correo electrónico. Pensado para clientes que no necesitan los XMLs o empresas extranjeras")

	def get_main_email(self):
		for email in self.emails_ids:
			if email.name and email.main_email:
				return email.name
		return self.email

	# Devuelve un string de correos electronicos del cliente separados por coma.
	def _get_emails(self):
		emails = list()
		main_email = False
		for email in self.emails_ids:
			if email.main_email:
				main_email = True
			if email.name and email.name not in emails and email.send_mail:
				emails.append(email.name)
		if not main_email and self.email and self.email not in emails:
			emails.append(self.email)
		return ', '.join(emails)

	@api.depends('state_id', 'county_id', 'district_id')
	def _compute_zip(self):
		for rec in self:
			if rec.country_id.code == 'CR' and rec.state_id and rec.county_id and rec.district_id:
				rec.zip = '%s%s%s' % (rec.state_id.fe_code, rec.county_id.code, rec.district_id.code)
			else:
				rec.zip = rec.zip

	def _get_cr_address_values(self):
		return [
			self.street,
			self.neighborhood_id.name,
			self.district_id.name,
			self.county_id.name,
			self.state_id.name,
			self.country_id.name,
		]

	@api.onchange('state_id')
	def onchange_state_id(self):
		self.county_id = False

	@api.onchange('county_id')
	def onchange_county_id(self):
		self.district_id = False

	@api.onchange('district_id')
	def onchange_district_id(self):
		self.neighborhood_id = False

	# # Se remplaza el metodo
	def _display_address(self, without_company=False):
		if self.country_id.code != 'CR':
			return super(PartnerElectronic, self)._display_address(without_company=without_company)
		full_address = ''
		address_values = self._get_cr_address_values()

		while address_values:
			value = address_values.pop(0)
			if value:
				full_address += value
			if address_values and value:
				full_address += ', '

		return full_address

	def get_valid_phone(self):
		return standard_tools.get_valid_phone(self.phone, self.phone_code)

	def get_valid_fax(self):
		return standard_tools.get_valid_phone(self.fax, self.fax_code)

	def action_consult_res_partner(self):
		if not self.ref:
			raise UserError('Por favor ingrese una cédula')

		values = dict()

		# todo Deshabilitado yo_contribuyo y pesca hasta que MH los arregle
		# response = self.yo_contribuyo()
		# if response and 'Resultado' in response:
		# 	values["email"] = ','.join([c['Correo'] for c in response['Resultado']['Correos']])
		#
		# response = self._consult_res_partner(url='https://api.hacienda.go.cr/fe/pesca?identificacion=', raise_error=False) or self._consult_res_partner()
		response = self._consult_res_partner()
		if response:
			tax_situation = response.get('situacionTributaria', response)
			action = self.sudo().env.ref('cr_electronic_invoice.action_res_partner_result_mh_wizard').read()[0]
			code = tax_situation.get('tipoIdentificacion')
			identification_type = self.env['identification.type'].search([('code', '=', code)], limit=1)
			situation = tax_situation.get('situacion')

			#todo ver key mensaje del response

			values.update({
				'res_partner_id': self.id,
				'name': tax_situation.get('nombre'),
				'identification_id': identification_type.id,
				'ref': self.ref,
				'regime': tax_situation.get('regimen').get('descripcion'),
				'defaulter': situation.get('moroso'),
				'omitted': situation.get('omiso'),
				'state': situation.get('estado'),
				'tax_administration': situation.get('administracionTributaria'),
			})

			result_wizard = self.env['res.partner.result.mh.wizard'].create(values)

			activities = tax_situation.get('actividades', [])
			for activity in activities:
				code = ('000000' + str(activity.get('codigo')))[-6:]
				self.env['res.partner.result.mh.activity.lines.wizard'].create({
					'res_partner_result_mh_id': result_wizard.id,
					'code': code,
					'name': str(activity.get('descripcion'))
				})

			# MAG
			mag_list = response.get('listaDatosMAG', [])
			for mag in mag_list:
				self.env['res.partner.result.mh.mag.lines.wizard'].create({
					'res_partner_result_mh_id': result_wizard.id,
					'type': 'mag',
					'due_date': datetime.strptime(mag.get('fechaBajaMAG'), "%Y/%m/%d"),
					'validity': mag.get('indicadorActivoMAG'),
				})
			# Incopesca
			mag_list = response.get('listaDatosIncopesca', [])
			for mag in mag_list:
				self.env['res.partner.result.mh.mag.lines.wizard'].create({
					'res_partner_result_mh_id': result_wizard.id,
					'type': 'incopesca',
					'due_date': mag.get('fechaVenceIncopesca') and datetime.strptime(mag.get('fechaVenceIncopesca'), "%Y/%m/%d") or False,
					'validity': bool(mag.get('indicadorActivoIncopesca')),
				})
			# Acuicultores
			mag_list = response.get('listaDatosAcuicultores', [])
			for mag in mag_list:
				self.env['res.partner.result.mh.mag.lines.wizard'].create({
					'res_partner_result_mh_id': result_wizard.id,
					'type': 'acuicultores',
					'due_date': datetime.strptime(mag.get('fechaVenceAcuicultor'), "%Y/%m/%d"),
					'validity': mag.get('indicadorActivoAcuicultor'),
				})

			action.update({
				'res_id': result_wizard.id
			})
			return action

	def yo_contribuyo(self, ref=False):
		if not ref:
			ref = self.ref

		# Pruebas 105760869

		# las credenciales solo funcionan con cedulas fisicas
		headers = {
			'Content-type': 'application/json;charset=UTF-8',
			'access-user': '116080531',
			'access-token': 'vE57tCIiFbHScQbFb5C4',
		}

		url = 'https://api.hacienda.go.cr/fe/mifacturacorreo?identificacion=%s' % ref

		try:
			response_document = requests.get(url, headers=headers)
			response_content = json.loads(str(response_document._content, 'utf-8'))
			return response_content
		except:
			return False

	def _consult_res_partner(self, url=None, raise_error=True, ref=False):
		if url is None:
			url = "https://api.hacienda.go.cr/fe/ae?identificacion="

		if not ref:
			ref = self.ref

		if ref:
			url += ref
			try:
				response_document = requests.get(url)
				response_content = json.loads(str(response_document._content, 'utf-8'))
			except:
				if raise_error:
					raise UserError('No fue posible obtener respuesta del servicio del Ministerio de Hacienda, por favor vuelva a intentarlo, si el problema persiste contacte con soporte.')
				return False

			if response_document.status_code == 200:
				return response_content
			elif response_document.status_code == 404:
				if raise_error:
					raise UserError('Contacto no encontrado en la base de datos de MH, Ced: ' + str(ref))
			else:
				return False
		else:
			return False

	@api.onchange('ref', 'company_id', 'type')
	def _onchange_ref(self):
		if self.ref and self.type != 'invoice':
			domain = [
				('ref', '=', self.ref),
				('type', '!=', 'invoice'),
				'|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
			]
			try:
				domain.append(('id', '!=', int(self.id)))
			except:
				pass

			partner = self.env['res.partner'].search(domain, limit=1)

			if partner:
				message_company = ''
				if partner.company_id:
					message_company = ', Compañía: ' + partner.company_id.name
				res = {
					'warning': {
						'title': 'Número de cédula duplicado',
						'message': 'El número de Cédula: ' + partner.ref + ' ya se encuentra registrado para el cliente: ' + (partner.name or '') + message_company
					}
				}
				return res

	# Validaciones
	@api.constrains('electronic_voucher_create_invoice')
	def _check_electronic_voucher_create_invoice(self):
		for rec in self:
			if rec.electronic_voucher_create_invoice:
				product_id_electronic_voucher = rec.product_id_electronic_voucher or rec.company_id.product_id_electronic_voucher or self.env.company.product_id_electronic_voucher

				if not product_id_electronic_voucher or not product_id_electronic_voucher.property_account_expense_id:
					raise ValidationError('Configure un "Producto por defecto" por contacto o por compañía para todos los proveedores. Este producto debe tener la “Cuenta de gastos” asignada')

	@api.constrains('emails_ids')
	def _check_emails(self):
		for rec in self:
			if rec.emails_ids:
				main_email = False
				for email in rec.emails_ids:
					if email.main_email and main_email:
						raise ValidationError('Solo se permite un correo principal para FE el cual será utilizado para el XML y reporte de factura')

					main_email = email.main_email

					if email.name:
						message = standard_tools.validate_email(email.name)
						if message:
							message += ', Correo: ' + email.name
							raise ValidationError(message)

	@api.constrains('ref', 'identification_id', 'type')
	def _check_identification(self):
		for rec in self:
			if rec.ref or rec.identification_id:
				if not rec.ref:
					raise ValidationError("Por favor ingrese una Cédula")
				if not rec.identification_id:
					raise ValidationError("Por favor ingrese un Tipo de identificación")

				message = standard_tools.validate_identification(rec.ref, rec.identification_id.code)

				# Usuario interno, se evita validar la web al crear un contacto con portal
				if not message and rec.ref and self.env.user.has_group('base.group_user') and rec.type != 'invoice':
					domain = [
						('id', '!=', int(rec.id)),
						('ref', '=', rec.ref),
						('type', '!=', 'invoice'),
						'|', ('company_id', '=', rec.company_id.id), ('company_id', '=', False)
					]

					partner = self.env['res.partner'].search(domain, limit=1)

					if partner:
						message = 'El número de Cédula: %s ya se encuentra registrado para el cliente: %s' % (partner.ref, partner.name)

				if message:
					raise ValidationError(message)

	@api.constrains('phone_code')
	def _check_phone_code(self):
		for rec in self:
			if rec.phone_code:
				message = standard_tools.validate_phone_code(rec.phone_code)
				if message:
					raise ValidationError(message)

	@api.constrains('phone')
	def _check_phone(self):
		for rec in self:
			if rec.phone:
				message = standard_tools.validate_phone(rec.phone)
				if message:
					raise ValidationError(message)

	@api.constrains('fax_code')
	def _check_fax_code(self):
		for rec in self:
			if rec.fax_code:
				message = standard_tools.validate_fax_code(rec.fax_code)
				if message:
					raise ValidationError(message)

	@api.constrains('fax')
	def _check_fax(self):
		for rec in self:
			if rec.fax:
				message = standard_tools.validate_fax(rec.fax)
				if message:
					raise ValidationError(message)

	# Valida el correo electronico
	@api.constrains('email')
	def _check_email(self):
		for rec in self:
			if rec.email:
				message = standard_tools.validate_email(rec.email)
				if message:
					raise ValidationError(message)
