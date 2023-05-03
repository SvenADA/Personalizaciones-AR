# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from . import standard_tools
from datetime import datetime
import pytz
import logging
import sys

_logger = logging.getLogger(__name__)


class ElectronicVoucherSupplier(models.Model):
	_name = "electronic.voucher.supplier"
	_inherit = ['mail.thread']
	_order = "id desc"
	_description = 'Comprobante Electrónico'

	def _get_default_invoice_supplier(self):
		default_invoice_id = self._context.get('default_invoice_id', False)
		return default_invoice_id

	def _get_current_company(self):
		return self.env.company

	def _domain_activity_type(self):
		company_id = self.env.company
		ids = company_id.activity_types.ids
		if ids:
			return [('id', 'in', ids)]
		else:
			return []

	number_electronic_supplier = fields.Char(string="Número electrónico comprobante", help="Numero electronico al dar respuesta a un comprobante de proveedor", required=False, copy=False, index=True, )
	number_electronic = fields.Char(string="Número electrónico", required=False, copy=False, index=True, )
	date_issuance = fields.Char(string="Fecha de emisión", required=False, copy=False)
	consecutive_number_receiver = fields.Char(string="Número Consecutivo Receptor", required=False, copy=False, readonly=True, index=True)
	state_tributacion = fields.Selection([
		('aceptado', 'Aceptado'),
		('rechazado', 'Rechazado'),
		('no_encontrado', 'No encontrado'),
		('error', 'Error'),
		('recibido', 'Recibido'),
		('procesando', 'Procesando'),
		('enviado', 'Enviado'),
		('enviado_error', 'Error al enviar'),
		('conexion_error', 'Fallo conexión'),
		('esperando', 'Esperando envío'),
		('consultar_error', 'Error al consultar'),
		('validating_signature', 'Validando firma'),
		('not_presentable', 'No presentable'),
	], 'Estado FE', copy=False)
	state_invoice_partner = fields.Selection([
		('1', 'Aceptado'),
		('2', 'Aceptacion parcial'),
		('3', 'Rechazado'),
	], 'Respuesta del Cliente', required=False, default='1', help='Estado que indica si la factura recibida esta correcta o no, si esta es aceptada será parte de los registros contables del Ministerio de Hacienda para la declaración de impuestos')
	xml_comprobante = fields.Binary(string="Comprobante XML", required=False, copy=False, attachment=True)
	fname_xml_comprobante = fields.Char(string="Nombre de archivo Comprobante XML", required=False, copy=False)
	xml_respuesta_tributacion = fields.Binary(string="Respuesta XML", required=False, copy=False, attachment=True)
	fname_xml_respuesta_tributacion = fields.Char(string="Nombre de archivo XML Respuesta Tributación", required=False, copy=False)
	xml_supplier_approval = fields.Binary(string="XML Proveedor", required=False, copy=False, attachment=True)
	fname_xml_supplier_approval = fields.Char(string="Nombre de archivo Comprobante XML proveedor", required=False, copy=False)
	amount_tax_electronic_invoice = fields.Char(string='Total  Impuestos', readonly=True)
	amount_total_electronic_invoice = fields.Char(string='Total', readonly=True)
	electronic_invoice_return_message = fields.Text(string='Mensaje', readonly=True)
	partner_id = fields.Many2one(comodel_name="res.partner", string="Proveedor", required=False)
	company_id = fields.Many2one(comodel_name="res.company", string="Compañía", required=False, default=_get_current_company)
	journal_id = fields.Many2one(comodel_name="account.journal", string='Diario', domain="[('type', '=', 'purchase'),('company_id','=',company_id)]")
	validate_date = fields.Date(string="Fecha de validación", required=False, tracking=True)
	supplier_xml = fields.Char(string="Emisor", required=False, copy=False, )
	supplier_ref_xml = fields.Char(string="Identificación", required=False, copy=False, )
	invoice_id = fields.Many2one(comodel_name="account.move", string="Factura de proveedor", required=False, copy=False, default=_get_default_invoice_supplier)
	consecutive_number_xml = fields.Char(string='Consecutivo', readonly=True)
	electronic_voucher_line_ids = fields.One2many('electronic.voucher.supplier.line', 'electronic_voucher_id', string='Lineas del comprobante', copy=False)
	currency = fields.Char(string='Moneda')
	reason_rejection = fields.Text(string="Razón", required=False, help="Razón por la cual se rechaza o se acepta parcialmente el comprobante XML.")
	iva_condition_id = fields.Many2one(comodel_name="iva.condition", string="Condición del IVA", required=False)
	accredit_tax = fields.Float(string="Impuesto Acreditar", required=False, digits=(20, 5))
	applicable_expenditure = fields.Float(string="Gasto Aplicable", required=False, digits=(20, 5))
	activity_type = fields.Many2one(comodel_name="activity.code", string="Actividad económica", required=False, copy=False, domain=_domain_activity_type)
	date_issuance_receiver = fields.Char(string="Fecha de envío", required=False, copy=False)
	total_other_charges = fields.Char(string="Total Otros Cargos", required=False, copy=False)
	exchange_rate = fields.Char(string="Tipo de cambio", required=False, copy=False)
	date_presentation = fields.Date(string="Fecha de presentación", required=False, readonly=False, help='Fecha de emisión de la factura electrónica de proveedor, se permite modificar para su uso en reportes.')
	send_consult_order = fields.Integer(string="Orden de envío y consulta", required=False, copy=False, default=1)
	type_document = fields.Selection(string="Tipo de documento", selection=[
		('01', 'Factura'),
		('02', 'Nota de Débito'),
		('03', 'Nota de Crédito'),
		('04', 'Tiquete'),
		('08', 'Factura de compra'),
		('09', 'Factura de Exportación'),
	], required=False, compute="_compute_type_document", store=True)
	other_information_line_ids = fields.One2many('electronic.voucher.supplier.other.information.line', 'electronic_voucher_id', string='Lineas otros datos', copy=False, help="Datos adicionales que son de libre estructura (OtroTexto, OtroContenido) agregados por el proveedor para una comunicación adicional, se cargan de forma jerárquica para su correcta lectura")

	# Campos logicos, no se guardan en la base de datos
	invisible_expenditure_accredit = fields.Boolean(string="Volver invisible Impuesto Acreditar y Gasto Aplicable", store=False, compute="_compute_expenditure_accredit")

	_rec_name = "consecutive_number_xml"

	@api.depends('consecutive_number_xml')
	def _compute_type_document(self):
		for rec in self:
			if rec.consecutive_number_xml:
				type_document = rec.consecutive_number_xml[8:10]
				if type_document in ('01', '02', '03', '04', '08', '09'):
					rec.type_document = type_document
				else:
					rec.type_document = False
			else:
				rec.type_document = False

	@api.constrains('accredit_tax')
	def _check_accredit_tax(self):
		if self.accredit_tax < 0:
			raise ValidationError('El impuesto a creditar no puede ser negativo')
		if round(self.accredit_tax, 5) > float(self.amount_tax_electronic_invoice or 0):
			raise ValidationError('El impuesto a creditar no puede ser mayor a los impuesto de la factura')

	def validate_xml_from_list(self):
		electronic_vouchers = self.env['electronic.voucher.supplier'].browse(self._context.get('active_ids', []))
		for ce in electronic_vouchers:
			if not ce.state_tributacion:
				ce.validate_xml()

	def validate_xml(self):
		if not self.state_invoice_partner:
			raise UserError('Por favor seleccione una respuesta')
		if not self.xml_supplier_approval:
			raise UserError('Seleccione un comprobante XML')
		if self.company_id not in self.env.user.company_ids:
			raise UserError('No tiene permitido validar CE de otras compañías')
		if not self.activity_type:
			raise UserError('Por favor seleccione una actividad económica')
		if not self.iva_condition_id:
			raise UserError('Por favor seleccione una condición del IVA')

		if self.invoice_id:
			self.invoice_id.receiver_message_id = self.id

		now_utc = datetime.now(pytz.timezone('UTC'))
		now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
		self.date_issuance_receiver = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
		date_cr = now_cr.strftime("%Y-%m-%d")
		self.validate_date = date_cr

		if self.type_document in ('03', '04'):
			self.state_tributacion = 'not_presentable'
			self.consecutive_number_receiver = False
		else:
			if self.state_invoice_partner == '1':
				sequence_id = self.journal_id.sequence_electronic_invoice_provider
				tipo = '05'
			if self.state_invoice_partner == '2':
				sequence_id = self.journal_id.partial_acceptance_sequence_id
				tipo = '06'
			if self.state_invoice_partner == '3':
				sequence_id = self.journal_id.rejection_sequence_id
				tipo = '07'
			sequence_fe = sequence_id.next_by_id()
			self.consecutive_number_receiver = str(self.journal_id.sucursal) + str(self.journal_id.terminal) + str(tipo) + str(sequence_fe)

			self.state_tributacion = 'esperando'

	def validate_from_invocie(self):
		if not self.state_tributacion:
			self.validate_xml()

	def _compute_expenditure_accredit(self):
		self._invisible_expenditure_accredit()

	@api.onchange('iva_condition_id', 'state_invoice_partner')
	def _onchange_expenditure_accredit(self):
		self._invisible_expenditure_accredit()
		if self.iva_condition_id and self.iva_condition_id.code == '04':
			self.accredit_tax = 0

	def _invisible_expenditure_accredit(self):
		if self.iva_condition_id and self.iva_condition_id.code == '05':
			self.invisible_expenditure_accredit = True
			return
		if self.state_invoice_partner == '3':
			self.invisible_expenditure_accredit = True
			return
		self.invisible_expenditure_accredit = False

	@api.onchange('accredit_tax')
	def _onchange_accredit_tax(self):
		self.applicable_expenditure = float(self.amount_tax_electronic_invoice) - self.accredit_tax

	@api.onchange('xml_supplier_approval')
	def _onchange_xml_supplier_approval(self):
		return self._validate_xml_restrictions(self, self.xml_supplier_approval)

	def _get_xml_restrictions_message(self, message):
		return {
			'value': {
				'xml_supplier_approval': False
			},
			'warning': {
				'title': 'Atención',
				'message': message,
			}
		}

	def _validate_xml_format(self, root):
		if not root.findall('Clave'):
			return self._get_xml_restrictions_message('El archivo xml no contiene el nodo Clave.')
		if not root.findall('FechaEmision'):
			return self._get_xml_restrictions_message('El archivo xml no contiene el nodo FechaEmision.')
		if not root.findall('Emisor'):
			return self._get_xml_restrictions_message('El archivo xml no contiene el nodo Emisor.')
		if not root.findall('Emisor')[0].findall('Identificacion'):
			return self._get_xml_restrictions_message('El archivo xml no contiene el nodo Identificacion.')
		if not root.findall('Emisor')[0].findall('Identificacion')[0].findall('Tipo'):
			return self._get_xml_restrictions_message('El archivo xml no contiene el nodo Tipo de Identificacion.')
		if not root.findall('Emisor')[0].findall('Identificacion')[0].findall('Numero'):
			return self._get_xml_restrictions_message('El archivo xml no contiene el nodo Numero.')
		if not (root.findall('ResumenFactura') and root.findall('ResumenFactura')[0].findall('TotalComprobante')):
			return self._get_xml_restrictions_message('No se puede localizar el nodo TotalComprobante.')
		if not root.findall('Receptor'):
			return self._get_xml_restrictions_message('El xml no contiene el nodo receptor')
		if not root.findall('Receptor')[0].find('Identificacion'):
			return self._get_xml_restrictions_message('El nodo receptor no contiene numero de identificacion')
		return {}

	# Se utiliza para caso especial de Compannias con el mismo VAT
	def get_company_xml(self, comprobante, root):
		company_xml = root.findall('Receptor')[0].find('Identificacion')[1].text
		return self.env['res.company'].search([
			('vat', '=', company_xml),
		], limit=1)

	def _validate_xml_restrictions(self, comprobante, xml):
		warning_message = ''
		if xml:
			root = standard_tools.xml_supplier_to_ET(xml)
			invalid_format = self._validate_xml_format(root)
			if invalid_format:
				return invalid_format

			company = self.get_company_xml(comprobante, root)
			if not company:
				return self._get_xml_restrictions_message('El receptor asociado al xml no corresponde con la identificación de la compañía.')

			comprobante.company_id = company
			comprobante.activity_type = company.activity_type

			if company.iva_condition_id:
				iva_condition_id = company.iva_condition_id
			else:
				iva_condition_id = self.env['iva.condition'].search([('code', '=', '01'), ], limit=1)
			comprobante.iva_condition_id = iva_condition_id

			journal = self.env['account.journal'].search([
				('type', '=', 'purchase'),
				('company_id', '=', company.id)
			], limit=1)

			consecutive_number_xml = root.findall('NumeroConsecutivo')[0].text
			type_doc = consecutive_number_xml[8:10]

			if type_doc == '08':
				warning_message += '\nLos documentos electrónicos de tipo Factura de Compra ya son presentados y aceptados automaticamente como gastos, no es necesario su aceptación manual'

			comprobante.consecutive_number_xml = consecutive_number_xml
			comprobante.journal_id = journal

			comprobante.supplier_xml = root.findall('Emisor')[0].find('Nombre').text
			supplier_ref_xml = root.findall('Emisor')[0].find('Identificacion')[1].text
			comprobante.supplier_ref_xml = supplier_ref_xml

			partner = self.env['res.partner'].search([
				('ref', '=', supplier_ref_xml),
				'|', ('company_id', '=', company.id), ('company_id', '=', False)
			], limit=1)
			comprobante.partner_id = partner

			voucher = self.env['electronic.voucher.supplier'].search([
				('number_electronic', '=', root.findall('Clave')[0].text)
			], limit=1)

			total_comprobante = root.findall('ResumenFactura')[0].findall('TotalComprobante')[0].text
			comprobante.amount_total_electronic_invoice = total_comprobante

			comprobante.number_electronic = root.findall('Clave')[0].text
			date_issuance = root.findall('FechaEmision')[0].text
			comprobante.date_issuance = date_issuance
			comprobante.date_presentation = datetime.strptime(date_issuance[:10], "%Y-%m-%d").date()

			total_impuesto = '0'
			if root.findall('ResumenFactura') and root.findall('ResumenFactura')[0].findall('TotalImpuesto'):
				total_impuesto = root.findall('ResumenFactura')[0].findall('TotalImpuesto')[0].text

			comprobante.amount_tax_electronic_invoice = total_impuesto
			comprobante.accredit_tax = float(total_impuesto)

			total_other_charges = '0'
			if root.findall('ResumenFactura')[0].findall('TotalOtrosCargos'):
				total_other_charges = root.findall('ResumenFactura')[0].findall('TotalOtrosCargos')[0].text

			comprobante.total_other_charges = total_other_charges

			# comprobante.electronic_voucher_line_ids.sudo().unlink()
			# Carga y creacion de las lineas de factura
			value = self._get_voucher_lines(root)

			value.update(self._get_other_information_line(root))

			currency = 'CRC'
			if root.findall('ResumenFactura')[0].findall('CodigoTipoMoneda'):
				currency = root.findall('ResumenFactura')[0].findall('CodigoTipoMoneda')[0].findall('CodigoMoneda')[0].text

			comprobante.currency = currency

			exchange_rate = '1'
			if root.findall('ResumenFactura')[0].findall('CodigoTipoMoneda') and root.findall('ResumenFactura')[0].findall('CodigoTipoMoneda')[0].findall('TipoCambio'):
				exchange_rate = root.findall('ResumenFactura')[0].findall('CodigoTipoMoneda')[0].findall('TipoCambio')[0].text

			comprobante.exchange_rate = exchange_rate

			if voucher:
				warning_message += '\nEl xml ya fue cargado anteriormente. Número Consecutivo Receptor: %s. Número de factura: %s. Número electrónico: %s.' % (voucher.consecutive_number_receiver, voucher.consecutive_number_xml, voucher.number_electronic)

			if warning_message != '':
				return {'warning': {'title': 'Atención', 'message': warning_message}, 'value': value}

			return {'value': value}

	# Se utiliza para validar el xml del correo electronico cargado
	def _validate_charge_email(self, xml):
		warning_message = ''
		value = {}

		root = standard_tools.xml_supplier_to_ET(xml)

		invalid_format = self._validate_xml_format(root)
		if invalid_format:
			return invalid_format

		company_xml = root.findall('Receptor')[0].find('Identificacion')[1].text

		# se aplica sudo, cuando se ejecuta manual el servidor de correo entrante se toma la compania actual
		company = self.env['res.company'].sudo().search([
			('vat', '=', company_xml),
		], limit=1)

		if not company:
			return {'value': {
				'xml_supplier_approval': False
			},
				'warning': {
					'title': 'Atención',
					'message': 'El receptor asociado al xml no corresponde con la identificación de la compañía.'
				}
			}

		consecutive_number_xml = root.findall('NumeroConsecutivo')[0].text
		type_doc = consecutive_number_xml[8:10]

		if type_doc == '08':
			warning_message += '\nLos documentos electrónicos de tipo Factura de Compra ya son presentados y aceptados automaticamente como gastos, no es necesario su aceptación manual'

		voucher = self.env['electronic.voucher.supplier'].sudo().search([
			('number_electronic', '=', root.findall('Clave')[0].text)
		], limit=1)

		if voucher.id:
			warning_message += '\nEl xml ya fue cargado anteriormente'

		if warning_message != '':
			return {'warning': {'title': 'Atención', 'message': warning_message}, 'value': value}

		return {'value': value}

	def _get_voucher_lines(self, root):
		lines_list = list()
		lines = root.findall('DetalleServicio') and root.findall('DetalleServicio')[0] or []
		if lines:
			for line in lines:
				detail = line.findall('Detalle')[0].text
				quantity = line.findall('Cantidad')[0].text
				unit_price = line.findall('PrecioUnitario')[0].text
				unit_measurement = line.findall('UnidadMedida')[0].text
				sub_total = line.findall('SubTotal')[0].text
				if line.findall('Descuento'):
					discount = line.findall('Descuento')[0].findall('MontoDescuento')[0].text
				else:
					discount = '0'

				exoneration = False
				taxs = ''
				total_tax_amount = 0.0
				amount_tax = 0.0
				tax_type_rate_ids = list()
				for tax in line.findall('Impuesto'):
					tax_rate = str(tax.findall('Tarifa')[0].text)
					amount_tax = float(tax.findall('Monto')[0].text)
					total_tax_amount += amount_tax
					taxs += tax_rate + '%' + ' ₡' + str(amount_tax) + ' '
					if tax.findall('Exoneracion'):
						exoneration = True

					type_tax = tax.findall('Codigo')[0].text
					rate_tax = False
					if tax.findall('CodigoTarifa'):
						rate_tax = tax.findall('CodigoTarifa')[0].text

					tax_type_rate = self.env['tax.type.rate'].search([
						('tax_type.code', '=', type_tax),
						('tax_rate.code', '=', rate_tax)
					], limit=1)

					if not tax_type_rate:
						tax_type = self.env['invoice.tax.type'].search([('code', '=', type_tax)], limit=1)
						tax_rate = self.env['invoice.tax.code.rate'].search([('code', '=', rate_tax)], limit=1)

						tax_type_rate = self.env['tax.type.rate'].create({
							'tax_type': tax_type.id,
							'tax_rate': tax_rate.id,
						})
					tax_type_rate_ids.append(tax_type_rate.id)

				if exoneration:
					total_tax_amount = float(line.findall('ImpuestoNeto')[0].text)

				if taxs == '':
					taxs = "Exento"

				dict_line = {
					'electronic_voucher_id': False,
					'detail': detail,
					'quantity': quantity,
					'unit_measurement': unit_measurement,
					'unit_price': unit_price,
					'discount': discount,
					'sub_total': sub_total,
					'taxs': taxs,
					'tax_type_rate_ids': [[6, False, tax_type_rate_ids]],
					'total_tax_amount': total_tax_amount,
					'amount_total_line': sub_total,
				}

				format_line = [0, False, dict_line]
				lines_list.append(format_line)

			for line in self.electronic_voucher_line_ids:
				format_line = [2, line.id]
				lines_list.append(format_line)

			return {'electronic_voucher_line_ids': lines_list}
		return {}
	
	def recursion_other_content(self, root, hierarchy_sequence=''):
		lines_list = list()

		if len(root) == 0:
			dict_line = {
				'electronic_voucher_id': False,
				'hierarchy_sequence': hierarchy_sequence,
				'label': root.tag,
				'code': root.attrib.get('codigo', False),
				'content': root.text,
			}

			format_line = [0, False, dict_line]
			return [format_line]
		elif root.tag not in ('OtroContenido', 'Otros'):
			dict_line = {
				'electronic_voucher_id': False,
				'hierarchy_sequence': hierarchy_sequence,
				'code': root.attrib.get('codigo', False),
				'label': root.tag,
			}

			format_line = [0, False, dict_line]
			lines_list.append(format_line)

		line_count = 1
		for line in root:
			if hierarchy_sequence != '':
				h_sequence = '%s.%s' % (hierarchy_sequence, line_count)
			else:
				h_sequence = str(line_count)
			lines_list.extend(self.recursion_other_content(line, hierarchy_sequence=h_sequence))
			line_count += 1
		return lines_list

	def _get_other_information_line(self, root):
		lines_list = list()
		lines = root.findall('Otros') and root.findall('Otros')[0] or []
		if lines:
			lines_list.extend(self.recursion_other_content(lines))

		# Se eliminan lineas anteriores
		for line in self.other_information_line_ids:
			format_line = [2, line.id]
			lines_list.append(format_line)

		return {'other_information_line_ids': lines_list}

	# Se extrae las configuraciones del pos
	def get_config(self):
		config = self.env['config.electronic.invoice'].search([('id', '=', 1)], limit=1)
		return config

	# Carga los xmls desde correo electronico
	@api.model
	def _charge_xml_supplier_from_email(self):

		# Configuraciones
		config = self.get_config()

		voucher_suppliers = self.env['electronic.voucher.supplier'].search([
			('xml_supplier_approval', '=', False),
			('consecutive_number_xml', '!=', False),
		])

		if config.mode_debug:
			msg = '\n---------------------------------\nIncio de ejecucion del cron: FE: Cargar comprobante electronico de proveedor recibido por correo \n\n---------------------------------\n'
			vouchers_str = 'id : Asunto'
			for voucher in voucher_suppliers:
				vouchers_str += '\n' + str(voucher.id) + ' : ' + str(voucher.consecutive_number_xml)
			_logger.info(msg + '\n---------------------------------\nResgistros cargados: \n' + vouchers_str + '\n\n---------------------------------\n')

		for voucher in voucher_suppliers:
			have_xml = False
			attachments = self.env['ir.attachment'].search([
				('res_id', '=', voucher.id),
				('res_model', '=', 'electronic.voucher.supplier'),
			])

			subject = voucher.consecutive_number_xml
			for attachment in attachments:
				name = str(attachment.name).lower()
				if name.find(".xml") >= 0:
					try:
						# se cargan los datos
						validate = self._validate_xml_restrictions(voucher, attachment.datas)
						warning = validate.get('warning', False)
						if not warning:
							voucher.write(validate.get('value'))
							voucher.fname_xml_supplier_approval = attachment.name
							attachment.res_field = 'xml_supplier_approval'
							have_xml = True
							voucher.consecutive_number_receiver = 'Cargado por Email, Asunto: ' + str(subject)
							try:
								if voucher.partner_id.electronic_voucher_create_invoice:
									voucher.create_invoice()
							except:
								voucher.electronic_invoice_return_message = 'Error al crear factura de proveedor: %s' % str(sys.exc_info())
								msg = 'Carga en CE, Error al crear factura: ' + str(sys.exc_info()) + "\nNombre de archivo: " + str(attachment.name)
								_logger.info(msg)
							break
						elif config.mode_debug:
							_logger.info('\n---------------------------------\nWarning xml: \n %s Nombre de archivo: %s\n\n---------------------------------\n' % (warning, attachment.name))

					except:
						msg = 'Carga en CE, Error al leer el xml: ' + str(sys.exc_info()) + "\nNombre de archivo: " + str(attachment.name)
						_logger.info(msg)
			if not have_xml:
				voucher.unlink()

	def action_create_invoice(self):
		wizard = self.env['purchase.invoice.wizard'].create({
			'electronic_voucher_supplier_id': self.id,
		})
		product_id = False
		account_id = False
		configured_product = False
		if self.partner_id and self.partner_id.product_id_electronic_voucher:
			product_id = self.partner_id.product_id_electronic_voucher.id
			account_id = self.partner_id.product_id_electronic_voucher.property_account_expense_id.id
			configured_product = True
		elif self.company_id.product_id_electronic_voucher:
			product_id = self.company_id.product_id_electronic_voucher.id
			account_id = self.company_id.product_id_electronic_voucher.property_account_expense_id.id
			configured_product = True

		for line in self.electronic_voucher_line_ids:
			self.env['purchase.invoice.line.wizard'].create({
				'purchase_invoice_wizard_id': wizard.id,
				'company_id': self.company_id.id,
				'detail': line.detail,
				'product_id': product_id,
				'account_id': account_id,
				'electronic_voucher_line_id': line.id,
			})

		action = self.sudo().env.ref('cr_electronic_invoice.action_purchase_invoice_wizard').read()[0]
		action.update(res_id=wizard.id, context={'configured_product': configured_product})
		return action

	def create_provider(self):
		root = standard_tools.xml_supplier_to_ET(self.xml_supplier_approval)
		root_emisor = root.findall('Emisor')[0]

		identification_code = root_emisor.findall('Identificacion')[0].findall('Tipo')[0].text
		identification_type = self.env['identification.type'].search([('code', '=', identification_code)], limit=1)
		email = False
		if root_emisor.findall('CorreoElectronico'):
			email = root.findall('Emisor')[0].findall('CorreoElectronico')[0].text

		root_ubicacion = root_emisor.findall('Ubicacion')[0]

		state_id = self.env['res.country.state'].search([
			('country_id', '=', self.env.ref("base.cr").id),
			('fe_code', '=', root_ubicacion.findall('Provincia')[0].text),
		], limit=1)

		county_id = self.env['res.country.county'].search([
			('state_id', '=', state_id.id),
			('code', '=', root_ubicacion.findall('Canton')[0].text),
		], limit=1)

		district_id = self.env['res.country.district'].search([
			('county_id', '=', county_id.id),
			('code', '=', root_ubicacion.findall('Distrito')[0].text),
		], limit=1)

		neighborhood_id = False
		if root_ubicacion.findall('Barrio'):
			neighborhood_id = self.env['res.country.neighborhood'].search([
				('district_id', '=', district_id.id),
				('code', '=', root_ubicacion.findall('Barrio')[0].text),
			], limit=1)

		phone = False
		if root_emisor.findall('Telefono') and root_emisor.findall('Telefono')[0].findall('NumTelefono'):
			phone = root_emisor.findall('Telefono')[0].findall('NumTelefono')[0].text

		trade_name = False
		if root_emisor.findall('NombreComercial'):
			trade_name = root_emisor.findall('NombreComercial')[0].text

		partner = self.env['res.partner'].create({
			'name': self.supplier_xml,
			'commercial_name': trade_name,
			'identification_id': identification_type.id,
			'ref': self.supplier_ref_xml,
			'email': email,
			'phone': phone,
			'supplier_rank': 1,
			'company_id': self.company_id.id,
			'state_id': state_id.id,
			'county_id': county_id.id,
			'district_id': district_id.id,
			'neighborhood_id': neighborhood_id and neighborhood_id.id or False,
			'street': root_ubicacion.findall('OtrasSenas')[0].text,
		})

		self.partner_id = partner

	def create_invoice(self, wizard=False):
		invoice_ids = list()
		for ce in self:
			if not ce.invoice_id:
				currency_id = self.env['res.currency'].search([
					('name', '=', ce.currency),
				], limit=1)
				journal_id = self.env['account.journal'].search([
					('type', '=', 'purchase'),
					('company_id', '=', ce.company_id.id),
				], limit=1)

				if not ce.partner_id:
					if ce.xml_supplier_approval:
						partner = self.env['res.partner'].search([
							('ref', '=', ce.supplier_ref_xml),
							'|', ('company_id', '=', ce.company_id.id), ('company_id', '=', False)
						], limit=1)

						if not partner:
							ce.create_provider()
						else:
							ce.partner_id = partner

				invoice_type = 'in_invoice'
				if ce.type_document == '03':
					invoice_type = 'in_refund'

				inv = self.env['account.move'].create({
					'move_type': invoice_type,
					'partner_id': ce.partner_id.id,
					'currency_id': currency_id.id,
					'journal_id': journal_id.id,
					'ref': ce.consecutive_number_xml,
					'invoice_origin': 'CE: ' + ce.consecutive_number_xml,
					'receiver_message_id': ce.id,
					'invoice_date': ce.date_presentation,
					'date': ce.date_presentation,
					'company_id': ce.company_id.id,
					'invoice_payment_term_id': ce.partner_id.property_supplier_payment_term_id.id,
				})

				if ce.partner_id and ce.partner_id.product_id_electronic_voucher and not wizard:
					product_id = ce.partner_id.product_id_electronic_voucher.id
					account_id = ce.partner_id.product_id_electronic_voucher.property_account_expense_id.id
				elif ce.company_id.product_id_electronic_voucher and not wizard:
					product_id = ce.company_id.product_id_electronic_voucher.id
					account_id = ce.company_id.product_id_electronic_voucher.property_account_expense_id.id
				else:
					product_id = False
					account_id = False

				invoce_lines = list()
				for line in ce.electronic_voucher_line_ids:
					uom_id = self.env['uom.uom'].search([('code', '=', line.unit_measurement)], limit=1)

					taxs = list()
					for tax_type_rate in line.tax_type_rate_ids:
						tax = self.env['account.tax'].search([
							('tax_type', '=', tax_type_rate.tax_type.id),
							('tax_rate', '=', tax_type_rate.tax_rate.id),
							('type_tax_use', '=', 'purchase'),
							('company_id', '=', ce.company_id.id),
						], limit=1)
						if tax:
							taxs.append(tax.id)

					disconunt_amount = float(line.discount or 0)
					if disconunt_amount:
						discount = (disconunt_amount / (float(line.quantity or 1) * float(line.unit_price or 1))) * 100
					else:
						discount = 0

					if wizard:
						for line_wizard in wizard.line_ids:
							if line_wizard.electronic_voucher_line_id.id == line.id:
								product_id = line_wizard.product_id.id
								account_id = line_wizard.account_id.id
								break

					dict_line = {
						'move_id': inv.id,
						'product_id': product_id,
						'account_id': account_id,
						'name': line.detail,
						'quantity': float(line.quantity or 0),
						'price_unit': float(line.unit_price or 0),
						'product_uom_id': uom_id.id,
						'discount': discount,
						'tax_ids': [[6, False, taxs]],
					}
					format_line = [0, False, dict_line]
					invoce_lines.append(format_line)

				if float(ce.total_other_charges):
					dict_line = {
						'move_id': inv.id,
						'account_id': account_id,
						'name': 'Total otros cargos',
						'quantity': 1,
						'price_unit': float(ce.total_other_charges),
						# 'product_uom_id': uom_id.id,
						'discount': 0,
						# 'account_id': inv.account_id.id,
						# 'tax_ids': [[6, False, taxs]],
					}
					format_line = [0, False, dict_line]
					invoce_lines.append(format_line)

				inv.write({'invoice_line_ids': invoce_lines})

				invoice_ids.append(inv.id)
				ce.invoice_id = inv.id

		result = self.sudo().env.ref('account.action_move_in_invoice_type').read()[0]
		result['domain'] = [('id', 'in', invoice_ids)]
		return result

	def get_state_invoice_partner_string(self):
		return dict(self.env['electronic.voucher.supplier'].fields_get(allfields=['state_invoice_partner'])['state_invoice_partner']['selection'])[self.state_invoice_partner]

	def name_get(self):
		state_tributacion = dict(self.env['electronic.voucher.supplier'].fields_get(allfields=['state_tributacion'])['state_tributacion']['selection'])
		result = []
		for voucher in self:
			if voucher.consecutive_number_receiver:
				state = state_tributacion.get(voucher.state_tributacion)
				result.append((voucher.id, str(state) + ': ' + voucher.consecutive_number_receiver + ' - ' + str(voucher.consecutive_number_xml)))
			else:
				if voucher.state_tributacion:
					not_sent = state_tributacion.get(voucher.state_tributacion)
				else:
					not_sent = "Sin enviar"
				result.append((voucher.id, not_sent + ": " + str(voucher.consecutive_number_xml)))
		return result

	def unlink(self):
		for ce in self:
			if ce.state_tributacion:
				raise UserError('No es permitido eliminar un comprobante ya validado')
		return super(ElectronicVoucherSupplier, self).unlink()


class ElectronicVoucherSupplierLine(models.Model):
	_name = "electronic.voucher.supplier.line"
	_description = 'Comprobante Electrónico Linea'

	electronic_voucher_id = fields.Many2one('electronic.voucher.supplier', string='Comprobante Electronico', ondelete='cascade', index=True)
	detail = fields.Char(string="Descripción", required=False, )
	quantity = fields.Char(string="Cantidad", required=False, )
	unit_measurement = fields.Char(string="Unidad de medida", required=False, )
	unit_price = fields.Char(string="Precio unitario", required=False, )
	sub_total = fields.Char(string="Subtotal", required=False, )
	discount = fields.Char(string="Monto de descuento", required=False, )
	taxs = fields.Char(string="Impuestos", required=False, help="Porcentaje (%) y Monto del impuesto (₡)")
	tax_type_rate_ids = fields.Many2many('tax.type.rate', string='Tarifa y Tipo de impuesto')
	total_tax_amount = fields.Char(string="Total Impuestos", required=False, )
	amount_total_line = fields.Char(string="Total", required=False, )


class TaxTypeRate(models.Model):
	_name = "tax.type.rate"
	_description = 'Tipo de impuesto y tarifa'

	tax_type = fields.Many2one(comodel_name="invoice.tax.type", string="Tipo de impuesto", )
	tax_rate = fields.Many2one(comodel_name="invoice.tax.code.rate", string="Tarifa")

	def name_get(self):
		result = list()
		for obj in self:
			result.append((obj.id, (obj.tax_rate.name or '') + ((obj.tax_rate and ', ') or '') + (obj.tax_type.name or '')))
		return result


class CreateVendorInvoiceWizard(models.TransientModel):
	_name = "create.vendor.invoice.wizard"
	_description = "Wizard para crear facturas de proveedor"

	def action_vendor_invoices(self):
		active_ids = self.env.context.get('active_ids')
		if not active_ids:
			return ''

		return {
			'name': 'Crear facturas de proveedor',
			'res_model': 'create.vendor.invoice.wizard',
			'view_mode': 'form',
			'view_id': self.env.ref('cr_electronic_invoice.create_vendor_invoice_wizard_view').id,
			'context': self.env.context,
			'target': 'new',
			'type': 'ir.actions.act_window',
		}

	def create_vendor_invoices(self):
		context = dict(self._context or {})
		active_ids = context.get('active_ids', []) or []
		electronic_vouchers = self.env['electronic.voucher.supplier'].browse(active_ids)
		return electronic_vouchers.create_invoice()


class ElectronicVoucherSupplierOtherInformationLine(models.Model):
	_name = "electronic.voucher.supplier.other.information.line"
	_description = 'Comprobante Electrónico Otra Información'

	electronic_voucher_id = fields.Many2one('electronic.voucher.supplier', string='Comprobante Electronico', ondelete='cascade', index=True)
	hierarchy_sequence = fields.Char(string="Secuencia de jerarquía", required=False, )
	label = fields.Char(string="Etiqueta", required=False, )
	code = fields.Char(string="Codigo", required=False, )
	content = fields.Text(string="Contenido", required=False, )
