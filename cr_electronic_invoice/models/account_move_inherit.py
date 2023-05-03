# -*- coding: utf-8 -*-
##############################################################################
#	Odoo Proprietary License v1.0
#	Copyright (c) 2019 Delfix Tecnosoluciones S.A. (http://www.delfixcr.com) All Rights Reserved.
##############################################################################
import json
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pytz
import base64
from datetime import datetime, timedelta
import sys
import random
from . import standard_tools
import re

_logger = logging.getLogger(__name__)

uom_service = ('Sp', 'Os', 'Spe', 'St', 'Alc', 'Al', 's', 'min', 'h', 'd', 'Cm', 'I')


class InvoiceLineElectronic(models.Model):
	_inherit = "account.move.line"

	discount_note = fields.Char(string="Nota de descuento", required=False, help="Naturaleza del descuento, si se deja vacío se enviara por defecto: Descuento comercial", size=80)


class AccountInvoiceElectronic(models.Model):
	_inherit = "account.move"

	def _get_default_type_document_selection(self):
		type_document = self._context.get('type_document', False)
		if type_document:
			if type_document == '02':
				return self.env['type.document.selection'].search([('code', '=', '02')], limit=1)
		return False

	def _get_default_activity_type(self):
		company = self.env.company
		if company and company.activity_type:
			return company.activity_type.id
		else:
			return False

	def _domain_activity_type(self):
		ids = False
		type = self._context.get('default_move_type', False)
		company_id = self.env.company
		# todo el self no trae la factura
		if type == 'in_invoice' and self.partner_id and self.type_document_selection and self.type_document_selection.code == '08':
			ids = self.partner_id.activity_types.ids
		elif company_id:
			ids = company_id.activity_types.ids

		if ids:
			return [('id', 'in', ids)]
		else:
			return []

	def _domain_type_document_selection(self):
		codes = list()
		type = self._context.get('default_move_type', False) or self.move_type
		if type == 'in_invoice':
			codes.append('08')
		elif type == 'out_invoice':
			codes.append('02')
			codes.append('09')

		if codes:
			return [('code', 'in', codes)]
		else:
			return []

	# Factura electronica
	number_electronic = fields.Char(string="Número electrónico", required=False, copy=False, index=True, )
	date_issuance = fields.Char(string="Fecha de emisión", required=False, copy=False)
	currency_rate_save = fields.Float(required=False, string="Valor del dolar")  # Tipo de cambio cuando se genero la factura
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
	], 'Estado FE', copy=False, help="""
	*Aceptado: La factura fue procesada correctamente por el MH.

	*Rechazado: La factura no fue aceptada por MH y se debe corregir de acuerdo al motivo de rechazo con una NC o ND.
	
	*No encontrado: Estado temporal, ocurrió un error en MH y el documento no es encontrado, se procederá a reintentar el reenvio de la factura después de 15 minutos.
	
	*Error: Estado temporal, ocurrió un error desconocido, se procederá a reintentar el reenvio de la factura después de 15 minutos.
	
	*Recibido: El MH recibe el documento pero todavía no lo ha procesado.
	
	*Procesando: El MH se encuentra procesando el mensaje de respuesta.
	
	*Enviado: El sistema envio la FE exitosamente.
	
	*Error al enviar: Estado temporal, hay un error o dato faltante en la factura, se procederá a reintentar el reenvio de la factura después de 15 minutos.
	
	*Fallo conexión con MH: El MH no se encuentra disponible y no se puede establecer una conexión.
	
	*Esperando envío: La factura fue válida y preparada para el envió al MH.
	
	*Error al consultar: Estado temporal, ocurre un error al consultar la factura, se procederá a reintentar la consulta de la factura después de 15 minutos.
	
	*Validando firma: Estado temporal, error de procesamiento de MH por el cual rechaza la FE, se procederá a consultar la factura después de 15 minutos.
	
	**Si los estados de error persisten o un estado como esperando envio, procesando, etc permanece estático por mucho tiempo,
	por favor contacte a soporte técnico.

	""")

	payment_methods_id = fields.Many2one(comodel_name="payment.methods", string="Método de Pago", required=False, copy=True)
	xml_respuesta_tributacion = fields.Binary(string="Respuesta XML", required=False, copy=False, attachment=True)
	fname_xml_respuesta_tributacion = fields.Char(string="Nombre de archivo XML Respuesta Tributación", required=False, copy=False)
	xml_comprobante = fields.Binary(string="Comprobante XML", required=False, copy=False, attachment=True)
	fname_xml_comprobante = fields.Char(string="Nombre de archivo Comprobante XML", required=False, copy=False)
	electronic_invoice_return_message = fields.Text(string='Mensaje', readonly=True, copy=False)
	type_document = fields.Char(string="Tipo de documento (xml)", required=False, compute="_compute_type_document", store=True, copy=False)
	nc_count = fields.Integer(string="Nota de Crédito", compute='_compute_invoice_reference_count', store=False)
	nd_count = fields.Integer(string="Nota de Débito", compute='_compute_invoice_reference_count', store=False)
	fe_count = fields.Integer(string="Referencias", compute='_compute_invoice_reference_count', store=False)
	activity_type = fields.Many2one(comodel_name="activity.code", string="Actividad económica", required=False, copy=True, default=_get_default_activity_type, domain=_domain_activity_type)
	receiver_message_id = fields.Many2one(comodel_name="electronic.voucher.supplier", string="Comprobante Electrónico", required=False, copy=False, )
	reference_document_ids = fields.One2many(comodel_name='reference.document.line', inverse_name='move_id', string='Líneas de documento de referencia', copy=False, compute='_compute_reference_document_ids', store=True)
	type_document_selection = fields.Many2one(comodel_name="type.document.selection", string="Tipo de documento", required=False, copy=True, domain=_domain_type_document_selection, default=_get_default_type_document_selection)
	special_tags_lines = fields.One2many(comodel_name="fe.special.tags.invoice.line", inverse_name="invoice_id", string="Líneas de etiquetas adicionales XML", required=False, copy=False, compute='_compute_special_tags_lines', store=True)
	invoice_attachment_ids = fields.One2many(comodel_name="electronic.invoice.email.attachment.line", inverse_name="invoice_attachment_id", string="Adjuntos", required=False, help="Documentos que serán enviados por correo electrónico junto a los archivos de la factura electrónica")

	# Comprobante electronico
	state_send_invoice = fields.Selection([
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
	], 'Estado FE Proveedor', copy=False, compute="_compute_voucher_info", store=True)
	amount_tax_electronic_invoice = fields.Monetary(string='Total de impuestos FE', compute="_compute_voucher_info", store=True)
	amount_total_electronic_invoice = fields.Monetary(string='Total FE', compute="_compute_voucher_info", store=True)
	not_validate_totals = fields.Boolean(string="Aceptar diferencia de totales", help="Si esta opción se activa, no se realizará la comparación entre el total de la factura y el total del comprobante xml de proveedor")
	send_consult_order = fields.Integer(string="Orden de envío y consulta", required=False, copy=False, default=1)

	# Campos logicos
	quantity_invoices_rejected = fields.Integer(string="Cantidad de factura rechazada del dia", required=False, compute="_compute_quantity_invoices_rejected", store=False)
	quantity_invoices_error = fields.Integer(string="Cantidad de factura error de ayer", required=False, compute="_compute_quantity_invoices_error", store=False)

	def _create_special_tags_lines(self, special_tags_lines, type_add):
		lines_list = list()
		for special_tag in special_tags_lines:

			if special_tag.add_in and self.move_type != special_tag.add_in:
				continue

			if special_tag.python_code:
				try:
					inv = self
					content = eval(special_tag.python_code)
				except:
					content = False
			else:
				content = special_tag.content

			dict_line = {
				'element': special_tag.element,
				'code': special_tag.code,
				'content_label': special_tag.content_label,
				'content': content,
				'required': special_tag.required,
				'read_only': special_tag.read_only,
				'read_only_content': special_tag.read_only_content,
				'python_code': special_tag.python_code,
				'type_add': type_add,
				'rel_id': special_tag.id,
			}

			format_line = [0, False, dict_line]
			lines_list.append(format_line)
		return lines_list

	def _compute_quantity_invoices_rejected(self):
		today = fields.Date.today()
		quantity_invoices_rejected = self.env['account.move'].search_count([('state_tributacion', '=', 'rechazado'), ('invoice_date', '=', today), ('state', '=', 'posted')])
		for inv in self:
			inv.quantity_invoices_rejected = quantity_invoices_rejected

	def action_quantity_invoices_rejected(self):
		today = fields.Date.today()
		invoices_rejected = self.env['account.move'].search([('state_tributacion', '=', 'rechazado'), ('invoice_date', '=', today), ('state', '=', 'posted')])

		action = {
			'name': 'Facturas Rechazadas',
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'views': [(False, 'list'), (False, 'form')],
			'domain': [('id', 'in', invoices_rejected.ids)],
		}
		return action

	def _compute_quantity_invoices_error(self):
		now_utc = datetime.now(pytz.timezone('UTC'))
		end_date = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
		start_date = end_date - timedelta(days=1)
		last_hour = end_date - timedelta(hours=1)

		invoices_error = self.env['account.move'].search_read([
			('state_tributacion', 'not in', ('aceptado', 'rechazado', False)),
			('invoice_date', '>=', start_date),
			('invoice_date', '<=', end_date),
			('state', '=', 'posted'),
			('date_issuance', '!=', False),
		], ['date_issuance'])
		quantity_invoices_error = 0
		for inv_dict in invoices_error:
			date_issuance = datetime.strptime(inv_dict.get('date_issuance'), "%Y-%m-%dT%H:%M:%S-06:00")
			if date_issuance.hour <= last_hour.hour or end_date.date() != date_issuance.date():
				quantity_invoices_error += 1

		for inv in self:
			inv.quantity_invoices_error = quantity_invoices_error

	def action_quantity_invoices_error(self):
		now_utc = datetime.now(pytz.timezone('UTC'))
		end_date = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
		start_date = end_date - timedelta(days=15)
		last_hour = end_date - timedelta(hours=1)

		invoices_error = self.env['account.move'].search_read([
			('state_tributacion', 'not in', ('aceptado', 'rechazado', False)),
			('invoice_date', '>=', start_date),
			('invoice_date', '<=', end_date),
			('state', '=', 'posted'),
			('date_issuance', '!=', False),
		], ['date_issuance'])
		invoices_error_ids = list()
		for inv_dict in invoices_error:
			date_issuance = datetime.strptime(inv_dict.get('date_issuance'), "%Y-%m-%dT%H:%M:%S-06:00")
			if date_issuance.hour <= last_hour.hour or end_date.date() != date_issuance.date():
				invoices_error_ids.append(inv_dict.get('id'))

		action = {
			'name': 'Facturas con error (Últimos 15 días)',
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
			'views': [(False, 'list'), (False, 'form')],
			'domain': [('id', 'in', invoices_error_ids)],
		}
		return action

	@api.depends('partner_id')
	def _compute_reference_document_ids(self):
		for inv in self:
			# Documento de Referencia para el ICE
			partner_id = inv.get_partner_to_ei(inv)
			if partner_id and partner_id.ref == '4000042139' and inv.move_type == 'out_invoice':
				if inv.reference_document_ids:
					inv.reference_document_ids = inv.reference_document_ids
				else:
					type_reference_document = self.env['type.reference.document'].search([('code', '=', '99')], limit=1)
					reference_code_id = self.env['reference.code'].search([('code', '=', '99')], limit=1)
					dict_line = {
						'type_reference_document_id': type_reference_document.id,
						'reference_code_id': reference_code_id.id,
						'reference_reason': 'Factura ICE',
					}
					format_line = [0, False, dict_line]
					inv.write({'reference_document_ids': [format_line]})
			else:
				inv.reference_document_ids = inv.reference_document_ids

	@api.depends('partner_id')
	def _compute_special_tags_lines(self):
		for inv in self:
			if inv.partner_id and inv.move_type in ('out_invoice', 'out_refund'):
				lines_list = list()
				line_company = False
				lines_ids = list()
				for line in inv.special_tags_lines:
					if line.type_add == 'res_partner':
						format_line = [2, line.id]
						lines_list.append(format_line)
						lines_ids.append(line.rel_id)
					elif line.type_add == 'res_company':
						line_company = True

				if inv.partner_id.is_special_taxpayer and inv.partner_id.special_tags_lines:
					if lines_ids != inv.partner_id.special_tags_lines.ids:
						lines = inv._create_special_tags_lines(inv.partner_id.special_tags_lines, 'res_partner')
						lines_list.extend(lines)
					else:
						lines_list = list()
				if inv.company_id and inv.company_id.special_tags_lines and (not line_company):
					lines = inv._create_special_tags_lines(inv.company_id.special_tags_lines, 'res_company')
					lines_list.extend(lines)

				if lines_list:
					inv.special_tags_lines = lines_list
				else:
					inv.special_tags_lines = inv.special_tags_lines
			else:
				inv.special_tags_lines = inv.special_tags_lines

	@api.onchange('partner_id', 'type_document_selection')
	def onchange_domain_activity_type(self):
		ids = False
		type = self._context.get('default_move_type', False)
		company_id = self.env.company
		if type == 'in_invoice' and self.partner_id and self.type_document_selection and self.type_document_selection.code == '08':
			ids = self.partner_id.activity_types.ids
			self.activity_type = self.partner_id.activity_type
		elif company_id:
			ids = company_id.activity_types.ids

		if ids:
			domain = {'activity_type': [
				('id', 'in', ids),
			]}
		else:
			domain = {'activity_type': []}
		return {'domain': domain}

	def _compute_invoice_reference_count(self):
		"""
		Recalcula las NC, ND, FE asociadas a la FE
		"""
		for record in self:
			references_list = list()
			references = self.env['reference.document.line'].search_read([('move_id.move_type', '=', 'out_refund'), ('invoice_id', '=', record.id)], fields=['id'])
			record.nc_count = len(references)
			references_list.extend([ref['id'] for ref in references])

			references = self.env['reference.document.line'].search_read([('move_id.move_type', '=', 'out_invoice'), ('invoice_id', '=', record.id), ('move_id.type_document', '=', '02')], fields=['id'])
			record.nd_count = len(references)
			references_list.extend([ref['id'] for ref in references])

			references = self.env['reference.document.line'].search_read([('invoice_id', '=', record.id), ('id', 'not in', references_list)], fields=['id'])
			record.fe_count = len(references)

	def action_view_nc(self):
		"""
		Muestra la vista lista de las notas de credito asociadas a la FE
		"""
		for inv in self:
			ids = list()
			references = self.env['reference.document.line'].search([('move_id.move_type', '=', 'out_refund'), ('invoice_id', '=', inv.id)])
			for ref in references:
				ids.append(ref.move_id.id)
			if ids:
				result = self.sudo().env.ref('account.action_move_out_refund_type').read()[0]
				domain = [('id', 'in', ids)]
				result['domain'] = domain
				return result

	def action_view_nd(self):
		"""
		Muestra la vista lista de las notas de debito asociadas a la FE
		"""
		for inv in self:
			ids = list()
			references = self.env['reference.document.line'].search([('move_id.move_type', '=', 'out_invoice'), ('invoice_id', '=', inv.id), ('move_id.type_document', '=', '02')])
			for ref in references:
				ids.append(ref.move_id.id)
			if ids:
				result = self.sudo().env.ref('cr_electronic_invoice.action_invoice_tree_nd').read()[0]
				domain = [('id', 'in', ids)]
				result['domain'] = domain
				return result

	def action_view_fe(self):
		"""
		Muestra la vista lista FE asociadas
		"""
		for inv in self:
			ids = list()
			references_list = list()

			references = self.env['reference.document.line'].search([('move_id.move_type', '=', 'out_refund'), ('invoice_id', '=', inv.id)])
			references_list.extend(references.ids)

			references = self.env['reference.document.line'].search([('move_id.move_type', '=', 'out_invoice'), ('invoice_id', '=', inv.id), ('move_id.type_document', '=', '02')])
			references_list.extend(references.ids)

			references = self.env['reference.document.line'].search([('invoice_id', '=', inv.id), ('id', 'not in', references_list)])
			for ref in references:
				ids.append(ref.move_id.id)

			if ids:
				result = self.sudo().env.ref('account.action_move_out_invoice_type').read()[0]
				domain = [('id', 'in', ids)]
				result['domain'] = domain
				return result

	@api.depends('receiver_message_id')
	def _compute_voucher_info(self):
		for inv in self:
			if inv.receiver_message_id:
				inv.state_send_invoice = inv.receiver_message_id.state_tributacion
				inv.amount_total_electronic_invoice = inv.receiver_message_id.amount_total_electronic_invoice
				inv.amount_tax_electronic_invoice = inv.receiver_message_id.amount_tax_electronic_invoice
			else:
				inv.state_send_invoice = False
				inv.amount_total_electronic_invoice = 0
				inv.amount_tax_electronic_invoice = 0

	@api.depends('type_document_selection', 'partner_id', 'receiver_message_id')
	def _compute_type_document(self):
		for inv in self:
			inv.type_document = inv._get_type_document()

	def _get_exoneration_documents(self):
		documents = list()
		if self.fiscal_position_id:
			for tax_line in self.fiscal_position_id.tax_ids:
				if tax_line.exoneration and tax_line.exoneration not in documents:
					documents.extend(tax_line.exoneration)
		return documents

	# Se extrae el nombre del tipo de documento
	def get_type_name_pdf(self, inv):
		type_document = inv.type_document
		if type_document == '01':
			return 'FE-'
		elif type_document == '02':
			return 'ND-'
		elif type_document == '03':
			return 'NC-'
		elif type_document == '04':
			return 'TE-'
		elif type_document == '08':
			return 'FEC-'
		elif type_document == '09':
			return 'FEE-'
		return ''

	def _get_type_document(self):
		type_document = ''

		if self.company_id.frm_ws_ambiente == 'disabled':
			return type_document

		if self.move_type == 'out_invoice':
			# FE
			type_document = '01'
			# FEE
			if self.type_document_selection and self.type_document_selection.code == '09':
				type_document = '09'
			# TE
			elif self.partner_id:
				partner_id = self.get_partner_to_ei(self)
				if not partner_id.identification_id or not partner_id.ref or (partner_id.identification_id and partner_id.identification_id.code == '05'):
					type_document = '04'
			# ND
			if self.type_document_selection and self.type_document_selection.code == '02':
				type_document = '02'
				return type_document
		# NC
		if self.move_type == 'out_refund':
			type_document = '03'
			return type_document

		if self.move_type == 'in_invoice':
			# FEC
			if self.type_document_selection and self.type_document_selection.code == '08':
				type_document = '08'
			# MR
			elif self.receiver_message_id:
				type_document = '05'

		return type_document

	def get_state_invoice_partner_string(self):
		return dict(self.env['account.move'].fields_get(allfields=['state_invoice_partner'])['state_invoice_partner']['selection'])[self.state_invoice_partner]

	def get_state_tributacion_string(self):
		return dict(self.env['account.move'].fields_get(allfields=['state_tributacion'])['state_tributacion']['selection'])[self.state_tributacion]

	@api.model
	def _consultahacienda_receptor(self):

		# Configuraciones
		config = self.get_config()

		if config.mode_debug:
			_logger.info('\n---------------------------------\nIncio de ejecucion del cron: FE: Consulta Hacienda Comprobantes\n---------------------------------\n')

		comprobantes = self.env['electronic.voucher.supplier'].search([
			('state_tributacion', 'in', ('enviado', 'recibido', 'procesando'))
		], limit=config.max_send_supplier, order="send_consult_order ASC")

		all_xml = []
		all_xml.extend(comprobantes)

		for inv in all_xml:
			inv.send_consult_order += 1

		if config.mode_debug:
			invoices_str = ''
			for inv in all_xml:
				invoices_str += '\n' + inv._name + ' : ' + str(inv.id) + ' Compannia: ' + str(inv.company_id.name)
			_logger.info('\n---------------------------------\nSe cargaron los comprobantes modelo:id' + invoices_str + '\n---------------------------------\n')

		self._process_consult_comprobante(all_xml, config)

	def _process_consult_comprobante(self, comprobantes, config):
		for comprobante in comprobantes:
			self._consult(comprobante, comprobante.number_electronic_supplier, config)
			if comprobante.invoice_id:
				comprobante.invoice_id.state_send_invoice = comprobante.state_tributacion
			if comprobante.state_tributacion == 'aceptado':
				self._send_email_supplier(comprobante)

	def _send_xml_supplier(self):
		# Configuraciones
		config = self.get_config()

		if config.mode_debug:
			_logger.info('\n---------------------------------\nIncio de ejecucion del cron: FE: Enviar comprobante electronico de proveedor\n---------------------------------\n')

		comprobantes = self.env['electronic.voucher.supplier'].search([
			('state_tributacion', '=', 'esperando')
		], limit=config.max_send_supplier, order="send_consult_order ASC")

		all_xml = []
		all_xml.extend(comprobantes)

		for inv in all_xml:
			inv.send_consult_order += 1

		if config.mode_debug:
			invoices_str = ''
			for inv in all_xml:
				invoices_str += '\n' + inv._name + ' : ' + str(inv.id) + ' Compannia: ' + str(inv.company_id.name)
			_logger.info('\n---------------------------------\nSe cargaron los comprobantes modelo:id' + invoices_str + '\n---------------------------------\n')

		self._process_comprobante(all_xml, config)

	def _process_comprobante(self, comprobantes, config):
		for comprobante in comprobantes:
			self._send_xml(comprobante, config)
			if comprobante.invoice_id:
				comprobante.invoice_id.state_send_invoice = comprobante.state_tributacion

	# Se envia el comprobante electronico del proveedor

	def _send_xml(self, comprobante, config):
		if comprobante.company_id.frm_ws_ambiente != 'disabled':
			if config.mode_debug:
				_logger.info('\n---------------------------------\nProcesando el comprobante modelo:id' + str(comprobante._name) + ' : ' + str(comprobante.id) + '\n---------------------------------\n')
			if comprobante.xml_supplier_approval:
				root = standard_tools.xml_supplier_to_ET(comprobante.xml_supplier_approval)

				if comprobante.state_invoice_partner == '1':
					detalle_mensaje = 'Aceptado'
					tipo = '05'
				if comprobante.state_invoice_partner == '2':
					detalle_mensaje = str(comprobante.reason_rejection)
					tipo = '06'
				if comprobante.state_invoice_partner == '3':
					detalle_mensaje = str(comprobante.reason_rejection)
					tipo = '07'

				payload = {
					'api_key': comprobante.company_id.api_key,
					'clave': {
						'tipo': tipo,
						'sucursal': comprobante.journal_id.sucursal,  # Se agrega la sucursal 001
						'terminal': comprobante.journal_id.terminal,  # Se agrega la terminal 00001
						'numero_documento': root.findall('Clave')[0].text,
						'numero_cedula_emisor': root.findall('Emisor')[0].find('Identificacion')[1].text,
						'fecha_emision_doc': comprobante.date_issuance_receiver,
						'mensaje': comprobante.state_invoice_partner,
						'detalle_mensaje': detalle_mensaje[:159],
						'total_factura': root.findall('ResumenFactura')[0].findall('TotalComprobante')[0].text,
						'numero_cedula_receptor': comprobante.company_id.vat,
						'num_consecutivo_receptor': comprobante.consecutive_number_receiver[-10:],
					},
					'emisor': {
						'identificacion': {
							'tipo': root.findall('Emisor')[0].findall('Identificacion')[0].findall('Tipo')[0].text,
							'numero': root.findall('Emisor')[0].findall('Identificacion')[0].findall('Numero')[0].text,
						},
					},
				}

				if comprobante.state_invoice_partner != '3':
					payload.get('clave').update({
						'condicion_impuesto': comprobante.iva_condition_id.code,
					})

				if comprobante.iva_condition_id.code != '05' and comprobante.state_invoice_partner != '3':
					payload.get('clave').update({
						'impuesto_acreditar': comprobante.accredit_tax,
						'gasto_aplicable': comprobante.applicable_expenditure,
					})

				if comprobante.iva_condition_id.code != '05':
					payload.get('clave').update({'codigo_actividad': comprobante.activity_type.code})

				if (root.findall('ResumenFactura') and root.findall('ResumenFactura')[0].findall('TotalImpuesto')):
					amount_tax_electronic_invoice = root.findall('ResumenFactura')[0].findall('TotalImpuesto')[0].text
					payload.get('clave').update(monto_total_impuesto=amount_tax_electronic_invoice)

				if config.mode_debug:
					_logger.info('\n---------------------------------\n' + 'Datos a enviar a MH: \n' + str(payload) + '\n---------------------------------\n')
				headers = {}
				if comprobante.company_id.frm_ws_ambiente == 'stag':
					requests_url = 'https://www.comprobanteselectronicoscr.com/api/acceptbounce.stag.43'
				else:
					requests_url = 'https://www.comprobanteselectronicoscr.com/api/acceptbounce.prod.43'
				response_content = ''
				try:
					response_document = requests.post(requests_url, headers=headers, data=json.dumps(payload))
					response_content = json.loads(str(response_document._content, 'utf-8'))
					if config.mode_debug:
						_logger.info('\n---------------------------------\n' + 'Respuesta de MH: \n' + str(response_content) + '\n---------------------------------\n')
						_logger.info('\n---------------------------------\n' + 'Codigo: ' + str(response_content.get('code')) + '\n---------------------------------\n')
					if response_content.get('code'):
						if str(response_content.get('code')) in ('1', '44'):
							comprobante.fname_xml_comprobante = 'ARC-' + comprobante.number_electronic + '-' + comprobante.consecutive_number_receiver + '.xml'
							self.env['ir.attachment'].create({
								'name': comprobante.fname_xml_comprobante,
								'type': 'binary',
								'datas': response_content.get('data'),
								'res_model': comprobante._name,
								'res_id': comprobante.id,
								'res_field': 'xml_comprobante',
								'mimetype': 'application/xml'
							})
							comprobante.state_tributacion = 'enviado'
							comprobante.electronic_invoice_return_message = False
							if str(response_content.get('code')) == '44':
								voucher = self.env['electronic.voucher.supplier'].search([('number_electronic_supplier', '=', response_content.get('clave'))], limit=1)
								if voucher:
									comprobante.electronic_invoice_return_message = 'Verificar  la  información  del  documento  enviado,  el  número  de consecutivo ya se encuentra registrado. Código 44'
									comprobante.state_tributacion = 'enviado_error'
							comprobante.number_electronic_supplier = response_content.get('clave')
						else:
							comprobante.electronic_invoice_return_message = 'Error al enviar el XML de proveedor: \n' + str(response_content)
							comprobante.state_tributacion = 'enviado_error'
				except:
					if config.mode_debug:
						_logger.info('\n---------------------------------\n' + 'Error al enviar el XML de proveedor: \n' + str(response_content) + 'Error interno de odoo al consultar la FE: ' + str(sys.exc_info()) + '\n---------------------------------\n')
					comprobante.electronic_invoice_return_message = 'Error al enviar el XML de proveedor: \n' + str(response_content) + 'Error interno de odoo: ' + str(sys.exc_info())  # Obtiene errores de python
					comprobante.state_tributacion = 'enviado_error'

	# Envia el correo electronico de respuesta a un XML de proveedor
	def _send_email_supplier(self, comprobante):
		try:

			if comprobante.company_id.template_email_voucher:
				template_obj = comprobante.company_id.template_email_voucher
			else:
				template_obj = self.env.ref('cr_electronic_invoice.template_electronic_voucher_supplier')

			attachments_xml = list()

			if comprobante.fname_xml_respuesta_tributacion:
				attachment = self.env['ir.attachment'].search([
					('res_model', '=', comprobante._name),
					('res_id', '=', comprobante.id),
					('res_field', '=', 'xml_respuesta_tributacion')
				], limit=1)
				attachments_xml.append(attachment.id)

			# Comprobante
			if comprobante.fname_xml_comprobante:
				attachment = self.env['ir.attachment'].search([
					('res_model', '=', comprobante._name),
					('res_id', '=', comprobante.id),
					('res_field', '=', 'xml_comprobante')
				], limit=1)
				attachments_xml.append(attachment.id)

			email_values = dict()
			email_values['attachment_ids'] = [(6, 0, attachments_xml)]
			template_obj.send_mail(comprobante.id, email_values=email_values, raise_exception=False, force_send=True)

			template_obj.attachment_ids = False
		except:
			comprobante.electronic_invoice_return_message = 'Fallo al enviar correo electronico: ' + str(sys.exc_info())

	@api.onchange('partner_id', 'company_id')
	def _onchange_partner_id(self):
		superr = super(AccountInvoiceElectronic, self)._onchange_partner_id()
		if self.partner_id:
			if self.partner_id.payment_methods_id:
				self.payment_methods_id = self.partner_id.payment_methods_id
			if self.move_type == 'out_invoice':
				if self.partner_id.export_invoice:
					self.type_document_selection = self.env['type.document.selection'].search([('code', '=', '09')], limit=1)

			if self.move_type == 'in_invoice':
				if self.partner_id.purchase_invoice:
					self.activity_type = self.partner_id.activity_type
					self.type_document_selection = self.env['type.document.selection'].search([('code', '=', '08')], limit=1)

		return superr

	# Valida si el cliente esta ligado a una empresa si es asi, se factura en nombre de la empresa
	def get_partner_to_ei(self, inv):
		if inv.partner_id.commercial_partner_id and inv.partner_id.type != 'invoice':
			partner_id = inv.partner_id.commercial_partner_id
		else:
			partner_id = inv.partner_id
		return partner_id

	# Se obtienen los documentos adjuntos para el correo electronico
	def _get_attachments_ids(self, inv):
		attachments_xml = []
		# Comprobante
		attachment = self.env['ir.attachment'].sudo().search([
			('res_model', '=', 'account.move'),
			('res_id', '=', inv.id),
			('res_field', '=', 'xml_comprobante'),
		], limit=1)
		if attachment:
			attachments_xml.append(attachment.id)

		# Si tiene Respuesta de hacienda
		attachment = self.env['ir.attachment'].sudo().search([
			('res_model', '=', 'account.move'),
			('res_id', '=', inv.id),
			('res_field', '=', 'xml_respuesta_tributacion'),
		], limit=1)
		if attachment:
			attachments_xml.append(attachment.id)

		# Se extrae el pdf de la factura
		type_invoice_name = self.get_type_name_pdf(inv)
		attachment_pdf = self.env['ir.attachment'].search([
			('res_model', '=', 'account.move'),
			('res_id', '=', inv.id),
			('name', '=', type_invoice_name + str(inv.number_electronic) + '.pdf')
		], limit=1)

		if attachment_pdf:
			attachments_xml.append(attachment_pdf.id)

		# Documentos adjuntos adicionales
		attachments_xml.extend(inv._get_additional_attachments_ids())

		return attachments_xml

	# Se obtienen los documentos adjuntos adicionales para el correo electronico
	def _get_additional_attachments_ids(self):
		attachments_ids = list()

		# Documentos en factura y documentos general desde la compannia

		invoice_attachment_ids = self.company_id.invoice_attachment_ids + self.invoice_attachment_ids

		for attachment in invoice_attachment_ids:
			attachment_obj = self.env['ir.attachment'].sudo().search([
				('res_model', '=', 'electronic.invoice.email.attachment.line'),
				('res_id', '=', attachment.id),
				('res_field', '=', 'email_attachment'),
			], limit=1)

			if attachment_obj:
				attachment_obj.name = attachment.fname_email_attachment
				attachments_ids.append(attachment_obj.id)

		return attachments_ids

	# Se envia correo electrobnico de factura electronica facturas de cliente
	def send_email_out_invoice(self, inv, manual_send=False):
		try:
			# Valida si el cliente esta ligado a una empresa si es asi, se factura en nombre de la empresa
			email_values = dict()
			partner_id = self.get_partner_to_ei(inv)
			emails = partner_id._get_emails()

			if emails and (not partner_id.not_send_mail_fe or manual_send):
				# Se carga la plantilla para el correo electronico
				email_template = inv.company_id.template_email_fe
				if not email_template:
					email_template = self.env.ref('account.email_template_edi_invoice', False)

				attachments_xml = self._get_attachments_ids(inv)
				email_values['attachment_ids'] = [(6, 0, attachments_xml)]
				email_values['email_to'] = emails
				email_template.send_mail(inv.id, email_values=email_values, raise_exception=False, force_send=True)
		except:
			inv.electronic_invoice_return_message = 'Error al enviar comprobante por correo electrónico: ' + str(sys.exc_info())

	# Se extrae las configuraciones del pos
	def get_config(self):
		config = self.env['config.electronic.invoice'].search([('id', '=', 1)], limit=1)
		return config

	@api.model
	def _consultahacienda(self):  # cron

		# limite de facturas a enviar
		config = self.get_config()

		if config.mode_debug:
			_logger.info('\n---------------------------------\nIncio de ejecucion del cron: FE: Consulta Hacienda\n---------------------------------\n')

		invoices = self.env['account.move'].search([
			('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice')),
			('state', '=', 'posted'),
			('number_electronic', '!=', False),
			('state_tributacion', 'in', ('enviado', 'recibido', 'procesando'))
		], limit=config.max_invoice_consult, order="send_consult_order ASC")

		if config.mode_debug:
			invoices_str = ''
			for inv in invoices:
				invoices_str += '\n' + str(inv.id) + ' : ' + str(inv.name) + ' Compannia: ' + str(inv.company_id.name)
			_logger.info('\n---------------------------------\nSe cargaron las facturas id : numero' + invoices_str + '\n---------------------------------\n')

		for inv in invoices:
			inv.send_consult_order += 1
			self._consult(inv, inv.number_electronic, config)

			if inv.state_tributacion == 'aceptado':
				self.send_email_out_invoice(inv)

	# Se utiliza para consultar facturas, comprobantes y facturas del POS
	def _consult(self, obj, number, config):
		if config.mode_debug:
			_logger.info('\n---------------------------------\nConsultando el id : modelo ' + str(obj.id) + ' : ' + str(obj._name) + ' Compannia: ' + str(obj.company_id.name) + '\n---------------------------------\n')

		if obj.company_id.frm_ws_ambiente == 'stag':
			requests_url = 'https://www.comprobanteselectronicoscr.com/api/consultahacienda.stag.43'
			frm_ws_ambiente = 'c3RhZw=='
		else:
			requests_url = 'https://www.comprobanteselectronicoscr.com/api/consultahacienda.prod.43'
			frm_ws_ambiente = 'cHJvZA=='
		payload = {
			'api_key': obj.company_id.api_key,
			'clave': number,
			'frm_ws_ambiente': frm_ws_ambiente
		}

		headers = {}

		response_content = ''
		try:
			response_document = requests.post(requests_url, headers=headers, data=json.dumps(payload))
			response_content = json.loads(str(response_document._content, 'utf-8'))
			if config.mode_debug:
				_logger.info('\n---------------------------------\nContenido de la consulta: ' + str(response_content) + '\n---------------------------------\n')
				_logger.info('\n---------------------------------\nCodigo: ' + str(response_content.get('code')) + '\n---------------------------------\n')

			if str(response_content.get('code')) == '1':
				if response_content.get('hacienda_result').get('ind-estado') == 'error':
					obj.state_tributacion = 'error'
				if response_content.get('hacienda_result').get('ind-estado') not in ['error']:

					if response_content.get('hacienda_result').get('ind-estado'):
						if config.mode_debug:
							_logger.info('\n---------------------------------\nRespuesta de consulta: ' + str(response_content.get('hacienda_result').get('ind-estado')) + '\n---------------------------------\n')
						obj.state_tributacion = response_content.get('hacienda_result').get('ind-estado')
						xml_response = response_content.get('hacienda_result').get('respuesta-xml')
						# Direntes modelos y campo
						if (obj._name == 'account.move') or obj._name == 'pos.order':
							obj.fname_xml_respuesta_tributacion = 'AHC-' + number + '.xml'
						else:
							obj.fname_xml_respuesta_tributacion = 'AHR-' + obj.number_electronic + '-' + obj.consecutive_number_receiver + '.xml'
						self.env['ir.attachment'].create({
							'name': obj.fname_xml_respuesta_tributacion,
							'type': 'binary',
							'datas': xml_response,
							'res_model': obj._name,
							'res_id': obj.id,
							'res_field': 'xml_respuesta_tributacion',
							'mimetype': 'application/xml'
						})
						root = standard_tools.xml_supplier_to_ET(xml_response)
						if root.findall('DetalleMensaje') != ' ':
							detalle = root.findall('DetalleMensaje')[0].text
						else:
							detalle = False
						obj.electronic_invoice_return_message = detalle
						if obj.state_tributacion == 'rechazado':

							state_temp = False
							if detalle.find("La firma del comprobante electrónico no es válida") >= 0:
								state_temp = 'validating_signature'
							if detalle.find("Rechazado, valorar reenvío.") >= 0:
								state_temp = 'esperando'

							if state_temp:
								now_utc = datetime.now(pytz.timezone('UTC'))
								date_now = now_utc.astimezone(pytz.timezone('America/Costa_Rica')).date()

								if obj._name == 'electronic.voucher.supplier':
									obj_date = obj.validate_date
								else:
									obj_date = datetime.strptime(obj.date_issuance, "%Y-%m-%dT%H:%M:%S-06:00").date()
								if abs(obj_date - date_now).days >= 3:
									obj.state_tributacion = 'rechazado'
								else:
									obj.state_tributacion = state_temp

					else:
						obj.electronic_invoice_return_message = 'Error de MH consultando el documento: \n' + str(response_content)
						obj.state_tributacion = 'consultar_error'

			elif str(response_content.get('code')) == '0':
				obj.state_tributacion = 'error'
				obj.electronic_invoice_return_message = 'Error de MH consultando el documento: \n' + str(response_content)
			elif str(response_content.get('code')) == '36':
				pass
			elif str(response_content.get('code')) == '33':
				obj.state_tributacion = 'no_encontrado'
			elif str(response_content.get('code')) == '47':
				obj.state_tributacion = 'enviado'
				obj.electronic_invoice_return_message = 'Consultando el documento: \n' + str(response_content.get('data', False))
			else:
				obj.electronic_invoice_return_message = 'Error de MH consultando el documento: \n' + str(response_content)
				obj.state_tributacion = 'consultar_error'
		except:
			if config.mode_debug:
				_logger.info('\n---------------------------------\n' + 'Error de MH consultando el documento: \n' + str(response_content) + 'Error interno de odoo al consultar la FE: ' + str(sys.exc_info()) + '\n---------------------------------\n')
			obj.electronic_invoice_return_message = 'Error de MH consultando el documento: \n' + str(response_content) + 'Error interno de odoo al consultar la FE: ' + str(sys.exc_info())  # Obtiene errores de python
			obj.state_tributacion = 'consultar_error'

	def _get_return_iva_total(self):
		if not self.company_id.tax_return_iva:
			tax_id = self.env.ref('cr_electronic_invoice.account_tax_return_iva', False)
		else:
			tax_id = self.company_id.tax_return_iva

		tax_repartition_lines = (self.move_type == 'out_refund' and tax_id.refund_repartition_line_ids or tax_id.invoice_repartition_line_ids).filtered(lambda x: x.repartition_type == 'tax')

		for line_tax in self.line_ids:
			if line_tax.account_id == tax_repartition_lines.account_id:
				return line_tax.price_unit

		return 0

	def _validate_electronic_restrictions(self):
		for inv in self:
			if inv.company_id.frm_ws_ambiente != 'disabled' and inv.type_document != '':

				if inv.company_id.expiration_date_p12 and datetime.now().date() == inv.company_id.expiration_date_p12:
					raise UserError('Error de Facturación Electrónica\n Llave Criptográfica expirada, por favor actualice la misma o contacte a soporte para su debido proceso.')

				# Valida si el cliente esta ligado a una empresa si es asi, se factura en nombre de la empresa
				partner_id = self.get_partner_to_ei(inv)

				for special_tag in inv.special_tags_lines:
					if special_tag.required and (not special_tag.content):
						raise UserError('Error de Facturación Electrónica\n Por favor verifique las líneas de datos adicionales e ingrese los datos requeridos.')

				# verifica que exista un reporte seleccionado en la compannia
				if not inv.company_id.report_invoice:
					raise UserError('Error de Facturación Electrónica\n Por favor seleccione en la compañía un informe de factura')

				if inv.move_type == 'in_invoice':
					# Validacion de la factura de compra
					if inv.type_document == '08':
						if not (partner_id.ref and partner_id.identification_id):
							raise UserError('Error de Facturación Electrónica\n La identificación y cedula es obligatorio para el proveedor')
						if not partner_id.state_id:
							raise UserError('Error de Facturación Electrónica\n La provincia es obligatoria para el proveedor')
						if not partner_id.county_id:
							raise UserError('Error de Facturación Electrónica\n El canton es obligatorio para el proveedor')
						if not partner_id.district_id:
							raise UserError('Error de Facturación Electrónica\n El distrito es obligatorio para el proveedor')
						if not partner_id.street:
							raise UserError('Error de Facturación Electrónica\n La dirección es obligatoria para el proveedor')
						if not partner_id.get_main_email():
							raise UserError('Error de Facturación Electrónica\n El correo electrónico es obligatorio para el proveedor')
						# if inv.name != '/':
						# 	raise UserError('Error de Facturación Electrónica\n Esta factura ya fue utilizada y cancelada por lo cual ya tiene una secuencia asignada que no es de Facturación Electrónica, recomendamos cancelar la factura y volver hacer una nueva')
						if partner_id.identification_id.code == '05':
							raise UserError('Error de Facturación Electrónica\n La identificación del proveedor es de tipo extranjero, la FEC solo permite emisores del Régimen Simplificado registrados en MH')

					elif inv.receiver_message_id:

						if inv.company_id.validate_pdf:

							attachments = self.env['ir.attachment'].search([
								'|',
								'&', ('res_model', '=', 'account.move'), ('res_id', '=', inv.id),
								'&', ('res_model', '=', 'electronic.voucher.supplier'), ('res_id', '=', inv.receiver_message_id.id),
							])

							is_pdf = False
							for attach in attachments:
								name = str(attach.name).lower()
								if name.find('.pdf') > 0:
									is_pdf = True
							if not is_pdf:
								raise UserError('Error de Facturación Electrónica\n Por favor agregue una documento pdf como adjunto')

						# Solo se comparan la parte entera
						if not inv.not_validate_totals:
							xml_total = round(float(inv.receiver_message_id.amount_total_electronic_invoice), 2)
							factura_total = float(inv.amount_total)
							if not xml_total == factura_total:
								raise UserError('Error de Facturación Electrónica\nEl monto total de la factura no coincide con el monto total del archivo XML\n Total de Factura: ' + str(factura_total) + '\n' + 'Total del comprobante electrónico: ' + str(xml_total))

						currency_code = inv.receiver_message_id.currency
						if (not (currency_code == inv.currency_id.name)) and currency_code:
							raise UserError('Error de Facturación Electrónica\nLa moneda de la factura es diferente a la moneda de la Factura electrónica. Moneda del comprobante electrónico: ' + str(currency_code))

						inv.receiver_message_id.invoice_id = inv.id
						inv.receiver_message_id.validate_from_invocie()
						inv.state_send_invoice = inv.receiver_message_id.state_tributacion

				cabys_allowed = list()
				exoneration_add = list()
				if inv.move_type == 'out_invoice':
					if inv.fiscal_position_id:
						for tax_line in inv.fiscal_position_id.tax_ids:
							if tax_line.exoneration:
								if tax_line.exoneration.due_date and tax_line.exoneration.due_date <= fields.Date.today():
									raise UserError('Error de Facturación Electrónica\nEl documento de exoneración: ' + tax_line.exoneration.name + ' se encuentra vencido')
								if tax_line.exoneration.validate_cabys and tax_line.exoneration.id not in exoneration_add:
									exoneration_add.append(tax_line.exoneration.id)
									cabys_allowed.extend([cabys.code for cabys in tax_line.exoneration.cabys_line_ids])

				# Validaciones para facturas de clientes y rectificativas
				if inv.move_type == 'out_invoice' or inv.move_type == 'out_refund' or inv.type_document == '08':

					if not inv.payment_methods_id:
						raise UserError('Error de Facturación Electrónica\nMétodo de Pago requerido')

					# Se valida que si tiene cedula o tipo de identificaion de un error de relcion
					if partner_id.identification_id or partner_id.ref:
						if not (partner_id.identification_id and partner_id.ref):
							raise UserError('Error de Facturación Electrónica del Cliente\nPor favor verifique que el cliente tenga tipo de identificación y cedula')

					# # Valida los campos identification_id y ref deacuerdo a su relacion entre ellos
					if partner_id.ref and partner_id.identification_id:
						message = standard_tools.validate_identification(partner_id.ref, str(partner_id.identification_id.code))
						if message:
							raise UserError('Error de Facturación Electrónica del Cliente\n' + message)

					# # Valida los campos identification_id y ref deacuerdo a su relacion entre ellos
					if partner_id.email:
						message = standard_tools.validate_email(partner_id.email)
						if message:
							raise UserError('Error de Facturación Electrónica del Cliente\n' + message)

					if inv.invoice_payment_term_id:
						if not inv.invoice_payment_term_id.sale_conditions_id:
							raise UserError('Error de Facturación Electrónica: \nDebe configurar condiciones de pago en el campo Plazo de Pago')

					# Validacion para notas de cretido y debito
					if inv.type_document in ('02', '03'):
						if not inv.reference_document_ids:
							raise UserError('Error de Facturación Electrónica\nPor favor ingrese al menos un documento de referencia')

					# Validacion de documentos de referencia
					for reference_document in inv.reference_document_ids:
						if not (reference_document.invoice_id or reference_document.external_document_id):
							raise UserError('Error de Facturación Electrónica\nPor favor ingrese al menos un documento de referencia en los campos "Documento" o "Documento Externo"')

					# Validacion de Orden del ICE, El codigo no siempre lo solicita el ICE
					if partner_id.ref == '4000042139' and inv.move_type == 'out_invoice' and inv.reference_document_ids:
						reference_document_no_found = True
						for reference_document in inv.reference_document_ids:
							if reference_document.external_document_id:
								reference_document_no_found = not any([reference_document.external_document_id.number_electronic.find(ice_code) >= 0 for ice_code in ('MM-', 'FI-', 'FT-')])

						if reference_document_no_found:
							raise UserError('Error de Facturación Electrónica\nPor favor ingrese la Orden del ICE con formato "MM-, FI-, FT-" en "Documentos de referencia" campo "Documento Externo"')

					# Valida que FEE no lleve exoneracion
					if inv.type_document == '09':
						if inv.fiscal_position_id:
							for tax_line in inv.fiscal_position_id.tax_ids:
								if tax_line.exoneration:
									raise UserError('Error de Facturación Electrónica\nLa Factura de Exportación no admite exoneraciones, si la exoneración es necesaria, por favor proceder a realizar una Factura Electrónica.')

					medio_pago = inv.payment_methods_id and inv.payment_methods_id.sequence
					# Se valida el descuento
					return_iva_total = 0.0
					for inv_line in inv.invoice_line_ids:
						# Valida que la linea tenga producto y descripcion
						if not inv_line.display_type:
							if not inv_line.tax_ids:
								raise UserError('Error de Facturación Electrónica\nTodas las líneas de la factura deben tener impuesto')

							for tax in inv_line.tax_ids:
								if inv.type_document == '09':
									if tax.tax_type.code != '00':
										raise UserError('Error de Facturación Electrónica\nLas facturas de exportación en general no deben llevar impuestos, por favor utilice el impuesto “Sin Impuesto del IVA” o uno que esté debidamente configurado.')

								if tax.other_charge and tax.other_charge.code not in ('06', '99') and len(inv_line.tax_ids) > 1:
									raise UserError('Error de Facturación Electrónica\nEl cargo: ' + str(tax.other_charge.name) + ' no puede estar junto a otros impuestos.')

							if inv.type_document == '09' and (not inv_line.product_id.tariff_item) and inv_line.product_id.type != 'service':
								raise UserError('Error de Facturación Electrónica\nTodos los productos de la factura de exportación deben de tener “Partida Arancelaria”.')
							if not inv_line.product_id or not inv_line.name:
								raise UserError('Error de Facturación Electrónica\nTodas las líneas de la factura deben tener producto y descripción')
							# Valida que no hayan lineas negativas en la factura
							if inv_line.quantity <= 0 or inv_line.price_unit < 0:
								raise UserError('Error de Facturación Electrónica\nNo se permite lineas de factura negativas\nNo se permite líneas con cantidad de producto en 0')
							if not inv_line.discount and inv_line.discount_note:
								inv_line.discount_note = False

							if not inv_line.product_uom_id:
								raise UserError('Error de Facturación Electrónica\nTodas las líneas de factura deben tener unidad de medida')

							# Se validan las unidades de medida de Servicios
							if inv_line.product_id and inv_line.product_uom_id:
								if not inv_line.product_uom_id.code:
									raise UserError('La unidad de medida: ' + str(inv_line.product_uom_id.name) + ', no posee código de Facturación Electrónica')
								if inv_line.product_id.type == 'service':
									if inv_line.product_uom_id.code not in uom_service:
										raise UserError('El producto: ' + str(inv_line.product_id.name) + ' es un servicio y su unidad de medida es: ' + str(inv_line.product_uom_id.name) + ', por favor proceder a modificar la unidad de medida de acuerdo al servicio. \n\n **La unidad de medida que se toma para el envío al MH se ubica en las líneas de facturas.')
								else:
									if inv_line.product_uom_id.code in uom_service:
										raise UserError('El producto: ' + str(inv_line.product_id.name) + ' es una mercancía y su unidad de medida es: ' + str(inv_line.product_uom_id.name) + ', por favor proceder a modificar la unidad de medida de acuerdo a la mercancía. \n\n **La unidad de medida que se toma para el envío al MH se ubica en las líneas de facturas.')
							# se valida cabys
							cabys_code = inv_line.product_id.get_cabys_code()
							if not cabys_code:
								raise UserError('El producto: ' + str(inv_line.product_id.name) + " no tiene asignado un código cabys, por favor proceda con su asignación en el producto o categoría.")

							if cabys_allowed and cabys_code not in cabys_allowed:
								raise UserError('El código cabys ' + cabys_code + ' del producto: ' + str(inv_line.product_id.name) + " no está permitido en la exoneración")

						# Logica para agregar a la linea de impuestos del IVA devuelto
						if inv.company_id.health_service and inv_line.product_id.type == 'service' and inv_line.product_id.return_iva and medio_pago == '02':
							return_iva_total += inv_line.price_total - inv_line.price_subtotal

					if return_iva_total:
						if not inv.company_id.tax_return_iva:
							tax_id = self.env.ref('cr_electronic_invoice.account_tax_return_iva', False)
						else:
							tax_id = inv.company_id.tax_return_iva

						tax_repartition_lines = (inv.move_type == 'out_refund' and tax_id.refund_repartition_line_ids or tax_id.invoice_repartition_line_ids).filtered(lambda x: x.repartition_type == 'tax')

						inv = inv.with_context(check_move_validity=False)
						line_tax_return_iva = False
						for line_tax in inv.line_ids:
							if line_tax.account_id == tax_repartition_lines.account_id:
								line_tax_return_iva = line_tax
								break

						for line_tax in inv.line_ids:
							if not line_tax.name and not line_tax.product_id and line_tax.exclude_from_invoice_tab:
								if line_tax_return_iva:
									line_tax.price_unit += line_tax_return_iva.price_unit

								line_tax.price_unit += return_iva_total
								break

						if line_tax_return_iva:
							line_tax_return_iva.price_unit = -return_iva_total
						else:
							dict_line = {
								'name': 'IVA Devuelto 4%',
								'move_id': inv.id,
								'account_id': tax_repartition_lines.account_id.id,
								'quantity': 1.0,
								'price_unit': -return_iva_total,
								'tax_exigible': True,
								'exclude_from_invoice_tab': True,
							}
							inv.line_ids.create(dict_line)

				# Configuracion del tipo de cambio
				# Guarda el tipo de cambio del dolar, se guarda antes por un requerimiento de un cliente
				if inv.company_id.currency_used:
					res_currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', inv.currency_id.id)], limit=1)
					currency_rate = 1 / (res_currency_rate.rate or 1)
				else:
					if inv.currency_id.name != 'CRC':
						currency_crc = self.env['res.currency'].search([('name', '=', 'CRC')], limit=1)
						currency_rate = currency_crc.rate
					else:
						currency_rate = 1

				if (inv.currency_id.name != 'CRC' and int(currency_rate) <= 100) or (inv.currency_id.name == 'CRC' and int(currency_rate) != 1):
					raise UserError('Error de Facturación Electrónica\n La moneda es: ' + str(inv.currency_id.name) + ' y el tipo de cambio es: ' + str(currency_rate) + ' por favor verificar el uso correcto del tipo de cambio.')

				inv.currency_rate_save = currency_rate

	def get_date_issuance_datetime(self):
		now_utc = datetime.now(pytz.timezone('UTC'))
		now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
		return now_cr

	def _generate_electronic_data(self):
		for inv in self:
			# Validaciones para facturas de clientes y rectificativas
			if inv.company_id.frm_ws_ambiente != 'disabled' and inv.type_document not in ('05', ''):

				# Se recalcula el campo dinamico de FE para las lineas de otros
				for special_tag in inv.special_tags_lines:
					if special_tag.python_code and (not special_tag.content):
						try:
							special_tag.content = eval(special_tag.python_code)
						except:
							pass

				now_cr = inv.get_date_issuance_datetime()
				inv.date_issuance = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")

				# Se genera el codigo de seguridad aleatorio
				security_code = ''
				for i in range(8):
					security_code += str(random.randint(0, 9))

				voucher_status = '1'
				if inv.reference_document_ids:
					for reference_document in inv.reference_document_ids:
						if reference_document.reference_code_id.code == '05':
							voucher_status = '2'

				# Se forma el nuemro de 50 digitos
				if not inv.number_electronic:
					number_50_digits = '506'  # Codigo pais
					number_50_digits += ('0' + str(now_cr.day))[-2:]  # dia 01
					number_50_digits += ('0' + str(now_cr.month))[-2:]  # mes 01
					number_50_digits += str(now_cr.year)[2:4]  # anno 18
					number_50_digits += ('0000' + inv.company_id.vat)[-12:]  # cedula empresa
					number_50_digits += inv.name  # Numero de factura de 20 digitos
					number_50_digits += voucher_status  # Estado de envio
					number_50_digits += security_code  # Codigo de seguridad
					inv.number_electronic = number_50_digits

				context = {
					'default_move_type': 'out_invoice',
					'lang': inv._context.get('lang', False),
					'tz': inv._context.get('tz', False),
					'uid': inv._context.get('uid', False),
				}
				pdf = inv.company_id.report_invoice.with_context(context)._render_qweb_pdf(inv.id)

				base64_pdf = base64.b64encode(pdf[0])
				type_invoice_name = self.get_type_name_pdf(inv)
				attachment_name = type_invoice_name + inv.number_electronic
				# Se crea el reporte pdf
				self.env['ir.attachment'].create({
					'name': attachment_name + '.pdf',
					'type': 'binary',
					'datas': base64_pdf,
					'res_model': inv._name,
					'res_id': inv.id,
					'mimetype': 'application/pdf'
				})

				inv.state_tributacion = 'esperando'

	def get_currency_rate(self, company_id, currency_id, date=None):
		# Configuracion del tipo de cambio
		# Se obtine el tipo de cambio
		if company_id.currency_used:
			if currency_id.name == 'CRC':
				currency_rate = 1
			else:
				if date:
					res_currency_rate = self.env['res.currency.rate'].search([
						('currency_id', '=', currency_id.id),
						('company_id', '=', company_id.id),
						('name', '<=', date),
					], limit=1, order='name desc')
					currency_rate = 1 / res_currency_rate.rate
				else:
					currency_rate = 1 / currency_id.rate
		else:
			if currency_id.name != 'CRC':
				currency_crc = self.env['res.currency'].search([('name', '=', 'CRC')], limit=1)
				if date:
					res_currency_rate = self.env['res.currency.rate'].search([
						('currency_id', '=', currency_crc.id),
						('company_id', '=', company_id.id),
						('name', '<=', date),
					], limit=1, order='name desc')
					currency_rate = res_currency_rate.rate
				else:
					currency_rate = currency_crc.rate
			else:
				currency_rate = 1
		return currency_rate

	def _set_sequence_electronic(self):
		for inv in self:
			if inv.type_document not in ('05', '') and inv.company_id.frm_ws_ambiente != 'disabled':
				inv.name = inv._get_sequence_electronic()

	def _post(self, soft=True):

		self._validate_electronic_restrictions()

		# FIX Cuando la factura es USD y es duplicada, los montos en colones de los apuntes contables no se actualizan al tipo de cambio del día
		for inv in self:
			if inv.company_id.currency_id != inv.currency_id and inv.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
				inv.with_context(check_move_validity=False)._onchange_currency()

		self._set_sequence_electronic()
		res = super(AccountInvoiceElectronic, self)._post(soft)
		self._generate_electronic_data()
		return res

	def decrease_send_consult_order(self):
		# El enviar, consultar y retry
		for inv in self:
			inv.send_consult_order -= 10

	# Las facuturas con estado de error al enviar se borra para que se vuelvan intentar enviar a MH
	@api.model
	def _retry_send_invoice(self, force_all=False):
		retry_send = ('enviado_error', 'conexion_error', 'error', 'no_encontrado')
		retry_consult = ('consultar_error', 'validating_signature')
		states = retry_send + retry_consult

		domain = [
			('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice')),
			('state', '=', 'posted'),
			('state_tributacion', 'in', states)
		]

		if not force_all:
			domain.append(('send_consult_order', '<=', 100))

		all_invoices = self.env['account.move'].search(domain)

		config = self.get_config()

		if config.mode_debug:
			_logger.info('\n---------------------------------\nIncio de ejecucion del cron: FE: Intentar envio de factura con errores\n---------------------------------\n')

		if config.mode_debug:
			invoices_str = ''
			for inv in all_invoices:
				invoices_str += '\n' + str(inv.id) + ' : ' + str(inv.name)
			_logger.info('\n---------------------------------\nSe cargaron las facturas id : numero' + invoices_str + '\n---------------------------------\n')

		for inv in all_invoices:
			if config.mode_debug:
				_logger.info('\n---------------------------------\nProcesando la factura id : numero ' + str(inv.id) + ' : ' + str(inv.name) + '\n---------------------------------\n')
			if inv.state_tributacion in retry_send:
				inv.state_tributacion = 'esperando'
			elif inv.state_tributacion in retry_consult:
				inv.state_tributacion = 'enviado'

		comprobantes = self.env['electronic.voucher.supplier'].search([
			('state_tributacion', 'in', states)
		])

		all_xml = []
		all_xml.extend(comprobantes)

		if config.mode_debug:
			invoices_str = ''
			for inv in all_xml:
				invoices_str += '\n' + inv._name + ' : ' + str(inv.id)
			_logger.info('\n---------------------------------\nSe cargaron los comprobantes modelo : id' + invoices_str + '\n---------------------------------\n')

		for comprobante in all_xml:
			if comprobante.state_tributacion in retry_send:
				comprobante.state_tributacion = 'esperando'
			elif comprobante.state_tributacion in retry_consult:
				comprobante.state_tributacion = 'enviado'

	# Se envia la factura a MH con un cron que se ejecuta cada minuto
	@api.model
	def _send_electronic_out_invoice(self, force_all=False):
		# limite de facturas a enviar
		config = self.get_config()

		if config.mode_debug:
			_logger.info('\n---------------------------------\nIncio de ejecucion del cron: FE: Crear Factura Electronica Clientes\n---------------------------------\n')

		domain = [
			('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice')),
			('state', '=', 'posted'),
			('state_tributacion', '=', 'esperando')
		]

		if not force_all:
			# Se agrega ('send_consult_order', '=', False) por que Odoo no mete los null
			domain.extend(['|', ('send_consult_order', '<=', 100), ('send_consult_order', '=', False)])

		# Extrae un numero determinado de facturas indicado por la compania
		all_invoices = self.env['account.move'].search(domain, limit=config.max_send_invoice, order="send_consult_order ASC")

		for inv in all_invoices:
			inv.send_consult_order += 1

		# Se guarda send_consult_order para controlar errores recurrentes
		self.env.cr.commit()

		if config.mode_debug:
			invoices_str = ''
			for inv in all_invoices:
				invoices_str += '\n' + str(inv.id) + ' : ' + str(inv.name) + ' Compannia: ' + str(inv.company_id.name)
			_logger.info('\n---------------------------------\nSe cargaron las facturas id : numero' + invoices_str + '\n---------------------------------\n')

		self._process_invoices(config, all_invoices)

	# Itera las factura y se plican sus respectivos metodos
	# Lista de clientes: Banco de Alimentos, Microtronics, Modulo cr_electronic_invoice_supermarket
	def _process_invoices(self, config, invoices):
		for inv in invoices:
			payload = self._create_payload(config, inv)
			self._send_invoice(config, inv, payload)

	# Se crea el json con los datos de las factura, Varios clientes Heredan el metodo
	def _create_payload(self, config, inv):
		if inv.company_id.frm_ws_ambiente != 'disabled':

			if config.mode_debug:
				_logger.info('\n---------------------------------\nProcesando la factura id : numero ' + str(inv.id) + ' : ' + str(inv.name) + '\n---------------------------------\n')

			type_document = inv.type_document

			now_cr = datetime.strptime(inv.date_issuance, "%Y-%m-%dT%H:%M:%S-06:00")
			referencia = list()
			medio_pago = (inv.payment_methods_id and inv.payment_methods_id.sequence) or '01'
			for reference_document in inv.reference_document_ids:
				codigo_referencia = reference_document.reference_code_id.code

				if reference_document.reference_reason:
					razon_referencia = reference_document.reference_reason[:179]
				else:
					razon_referencia = reference_document.reference_code_id.name

				tipo_documento_referencia = reference_document.type_reference_document_id.code

				if reference_document.external_document_id:
					numero_documento_referencia = reference_document.external_document_id.number_electronic
					fecha_emision_referencia = reference_document.external_document_id.date_issuance
					reference_document.external_document_id.is_validate = True
				else:
					if reference_document.invoice_id.number_electronic and len(reference_document.invoice_id.number_electronic) == 50:
						numero_documento_referencia = reference_document.invoice_id.number_electronic
						fecha_emision_referencia = reference_document.invoice_id.date_issuance
					else:
						if standard_tools.validate_whole_number(reference_document.invoice_id.name or reference_document.invoice_id.name):
							numero_documento_referencia = reference_document.invoice_id.name or reference_document.invoice_id.name
						else:
							# Elimina las letras del numero de factura
							numero_documento_referencia = standard_tools.delete_letters(reference_document.invoice_id.name or reference_document.invoice_id.name)
						if len(numero_documento_referencia) < 50:
							dif = 50 - len(numero_documento_referencia)
							numero_documento_referencia = (('0' * dif) + str(numero_documento_referencia))
						date_invoice = datetime.strptime(str(reference_document.invoice_id.invoice_date), "%Y-%m-%d")
						fecha_emision_referencia = date_invoice.strftime("%Y-%m-%d") + "T12:00:00-06:00"

				referencia.append({
					'tipo_documento': tipo_documento_referencia,
					'numero_documento': numero_documento_referencia,
					'fecha_emision': fecha_emision_referencia,
					'codigo': codigo_referencia,
					'razon': razon_referencia,
				})

			# Referencia para las factura de compra
			if type_document == '08':
				tipo_documento_referencia = '14'

				numero_documento_referencia = standard_tools.delete_letters(inv.ref)
				dif = 50 - len(numero_documento_referencia)
				numero_documento_referencia = (('0' * dif) + str(numero_documento_referencia))

				date_invoice = datetime.strptime(str(inv.invoice_date), "%Y-%m-%d")
				fecha_emision_referencia = date_invoice.strftime("%Y-%m-%d") + "T12:00:00-06:00"

				codigo_referencia = '04'
				razon_referencia = "Comprobante aportado por contribuyente del Regimen Simplificado"

				referencia.append({
					'tipo_documento': tipo_documento_referencia,
					'numero_documento': numero_documento_referencia,
					'fecha_emision': fecha_emision_referencia,
					'codigo': codigo_referencia,
					'razon': razon_referencia,
				})

			lines = []
			numero = 0

			# Valida si el cliente esta ligado a una empresa si es asi, se factura en nombre de la empresa
			partner_id = self.get_partner_to_ei(inv)

			if partner_id.identification_id.code == '05':
				receptor_identificacion = {
					'tipo': False,
					'numero': False,
				}
				receptor_identificacion_extranjero = partner_id.ref
			else:
				receptor_identificacion = {
					'tipo': partner_id.identification_id.code,
					'numero': partner_id.ref,
				}
				receptor_identificacion_extranjero = ''

			totalserviciogravado = 0.0
			totalservicioexento = 0.0
			totalmercaderiagravado = 0.0
			totalmercaderiaexento = 0.0
			totalservexonerado = 0.0
			totalmercexonerada = 0.0
			resumen_total_discount = 0
			impuestos_total = 0
			totalcomprobante = 0
			total_iva_devuelto = 0.0
			total_exoneracion = 0.0
			total_otros_cargos = 0.0
			otros_cargos = dict()
			for inv_line in inv.invoice_line_ids:
				if not inv_line.display_type:
					total_exoneracion_line = 0
					impuestos_acumulados = 0
					iva_acumulado = 0
					impuestos = []
					discount_line = 0
					discount_note_tmp = False
					quantity_line = standard_tools.round_decimal(inv_line.quantity, 3)
					price_unit_line = standard_tools.round_decimal(inv_line.price_unit, 5)
					tax_id = False
					is_charge_line = False

					tax_iva = list()
					tax_ids = list()
					price_include_tax = 0
					for tax_id in inv_line.tax_ids:
						if tax_id.price_include:
							price_include_tax += tax_id.amount

						if tax_id.tax_type.code == '01':
							# Se ordena para calcular de ultimo el impuesto de ventas (IVA), Solo debe haber 1 IVA
							tax_iva.append(tax_id)
						else:
							tax_ids.append(tax_id)

					if tax_iva:
						# Se calcula sobre el acumulado
						tax_ids.extend(tax_iva)

					if price_include_tax:
						price_unit_line = standard_tools.round_decimal(price_unit_line / ((price_include_tax / 100) + 1), 5)

					for tax_id in tax_ids:
						if (tax_id.tax_type and tax_id.tax_type.code != '00') or (inv.fiscal_position_id and not tax_id.other_charge):
							discont_apli = standard_tools.round_decimal(price_unit_line * (1 - (inv_line.discount or 0.0) / 100.0), 5)
							# Se ordena la lista porque el impuesto de venta se cancula sobre el acumulado de impuestos de otros tipos

							impuesto = dict()
							if inv.fiscal_position_id:
								old_tax = False
								doc_exoneration = False

								if len(inv.fiscal_position_id.tax_ids) > 1:
									for product_tax in inv_line.product_id.taxes_id:
										for tax_line in inv.fiscal_position_id.tax_ids:
											if tax_line.tax_src_id.id == product_tax.id:
												old_tax = tax_line.tax_src_id
												doc_exoneration = tax_line.exoneration

								if not old_tax:
									for tax_line in inv.fiscal_position_id.tax_ids:
										if tax_line.tax_dest_id.id == tax_id.id:
											old_tax = tax_line.tax_src_id
											doc_exoneration = tax_line.exoneration
											break

								if old_tax and doc_exoneration:
									tax_id = old_tax

									if tax_id.amount < doc_exoneration.purchase_percentage:
										purchase_percentage = int(tax_id.amount)
										purchase_percentage_base = int(tax_id.amount)
									else:
										purchase_percentage = doc_exoneration.purchase_percentage
										purchase_percentage_base = int(tax_id.amount)

									montoimpuesto = ((quantity_line * discont_apli) + impuestos_acumulados) * (purchase_percentage / 100.0)
									montoimpuesto = standard_tools.round_decimal(montoimpuesto, 5)
									total_exoneracion_line += montoimpuesto
									total_exoneracion += montoimpuesto
									exoneracion = {
										'exoneracion': {
											'tipodocumento': str(doc_exoneration.document_type_id.code),
											'numerodocumento': str(doc_exoneration.document_number),
											'nombreinstitucion': str(doc_exoneration.institution_name),
											'fechaemision': str(doc_exoneration.date_issue) + "T" + doc_exoneration.time_issue + "-06:00",
											'montoexoneracion': montoimpuesto,
											'porcentajeexoneracion': purchase_percentage,
										}}
									impuesto.update(exoneracion)

							if tax_id.tax_type.code == '01':
								impuesto_num = standard_tools.round_decimal(((quantity_line * discont_apli) + impuestos_acumulados) * ((tax_id.amount or 0.0) / 100.0), 5)
								iva_acumulado += impuesto_num
							else:
								impuesto_num = standard_tools.round_decimal(quantity_line * discont_apli * ((tax_id.amount or 0.0) / 100.0), 5)

							if tax_id.tax_type and tax_id.tax_type.code != '00':
								impuesto.update({
									'codigo': tax_id.tax_type.code,
									'codigotarifa': tax_id.tax_rate.code,
									'tarifa': tax_id.amount,
									'monto': impuesto_num,
								})

								if type_document == '09':
									impuesto.update({'exportacion': impuesto_num})

								impuestos.append(impuesto)

								impuestos_acumulados += impuesto_num
								impuestos_total += impuesto_num

						elif tax_id.other_charge:
							if tax_id.amount != 0:
								discont_apli = standard_tools.round_decimal(price_unit_line * (1 - (inv_line.discount or 0.0) / 100.0), 5)
								otros_cargos_amount = standard_tools.round_decimal(quantity_line * discont_apli * ((tax_id.amount or 0.0) / 100.0), 5)
							else:
								is_charge_line = True
								otros_cargos_amount = standard_tools.round_decimal(inv_line.price_subtotal, 5)

							if otros_cargos.get(tax_id.other_charge.code, False):
								charge = otros_cargos.get(tax_id.other_charge.code)
								charge.update(total=otros_cargos_amount + charge['total'])
							else:
								otros_cargos.update({
									tax_id.other_charge.code: {
										'name': tax_id.other_charge.name,
										'rate': tax_id.amount,
										'total': otros_cargos_amount,
									}
								})

					if not is_charge_line:
						numero += 1
						sud_total = standard_tools.round_decimal(price_unit_line * quantity_line, 6)
						sud_total = standard_tools.round_decimal(sud_total, 5)
						totalcomprobante += sud_total

						if inv_line.discount:
							discount_line = standard_tools.round_decimal(quantity_line * price_unit_line * ((inv_line.discount or 0.0) / 100.0), 5)
							resumen_total_discount += discount_line
							discount_note_tmp = (inv_line.discount_note or 'Descuento comercial')[:79]

						m_s_gravado = 0
						m_s_exonerado = 0
						m_s_exento = 0
						if (impuestos_acumulados or (tax_id and tax_id.tax_type and tax_id.tax_type.code == '01')) and not total_exoneracion_line:
							m_s_gravado = sud_total
						elif total_exoneracion_line:
							percentage_exo = purchase_percentage / purchase_percentage_base
							m_s_exonerado = standard_tools.round_decimal(sud_total * percentage_exo, 5)
							m_s_gravado = standard_tools.round_decimal(sud_total * (1 - percentage_exo), 5)
						else:
							m_s_exento = sud_total

						if inv_line.product_id.type == 'service':
							# Servicios
							totalserviciogravado += m_s_gravado
							totalservexonerado += m_s_exonerado
							totalservicioexento += m_s_exento
						else:
							# Mercancias
							totalmercaderiagravado += m_s_gravado
							totalmercexonerada += m_s_exonerado
							totalmercaderiaexento += m_s_exento

						impuesto_neto = standard_tools.round_decimal(iva_acumulado - total_exoneracion_line, 5)

						line = {
							'numero': numero,
							'codigo_hacienda': inv_line.product_id.get_cabys_code(),
							'codigo': [{
								'tipo': inv_line.product_id.code_type_id.code or '04',
								'codigo': (inv_line.product_id.default_code and str(inv_line.product_id.default_code)[:20]) or '000',
							}],
							'cantidad': quantity_line,
							'unidad_medida': inv_line.product_uom_id.code or 'Sp',
							'unidad_medida_comercial': inv_line.product_id.commercial_measurement,
							'detalle': inv_line.name[:159],
							'precio_unitario': price_unit_line,
							'monto_total': standard_tools.round_decimal(sud_total, 5),
							'descuento': [{
								'monto': standard_tools.round_decimal(discount_line, 5) or '',
								'naturaleza': discount_note_tmp or '',
							}],
							'subtotal': standard_tools.round_decimal(sud_total - discount_line, 5),
							'impuestos': impuestos or '',
							'impuestoneto': impuesto_neto,
							'montototallinea': standard_tools.round_decimal(sud_total - discount_line + impuestos_acumulados - total_exoneracion_line, 5),
						}

						if type_document == '09':
							line.update({'partida': inv_line.product_id.tariff_item})

						# Se suma el impuesto cuando el es un servico de salud
						if inv.company_id.health_service and inv_line.product_id.type == 'service' and inv_line.product_id.return_iva and medio_pago == '02':
							total_iva_devuelto += impuesto_neto

						lines.append(line)

			# Factura electronica o Factura de compra
			if type_document == '08':
				receptor = {
					'receptor': {
						'nombre': inv.company_id.name[:99],
						'identificacion': {
							'tipo': inv.company_id.identification_id.code,
							'numero': inv.company_id.vat,
						},
						'nombre_comercial': inv.company_id.commercial_name or '',
						'ubicacion': {
							'provincia': inv.company_id.state_id.fe_code,
							'canton': inv.company_id.county_id.code,
							'distrito': inv.company_id.district_id.code,
							'barrio': inv.company_id.neighborhood_id.code,
							'sennas': inv.company_id.street[:159],
						},
						'telefono': {
							'cod_pais': inv.company_id.phone_code,
							'numero': inv.company_id.get_valid_phone(),
						},
						'fax': {
							'cod_pais': inv.company_id.fax_code,
							'numero': inv.company_id.get_valid_fax(),
						},
						'correo_electronico': inv.company_id.email,
					}
				}

				emisor = {
					'emisor': {
						'nombre': partner_id.name[:99],
						'identificacion': receptor_identificacion,
						# 'IdentificacionExtranjero': receptor_identificacion_extranjero,
						'ubicacion': {
							'provincia': partner_id.state_id.fe_code,
							'canton': partner_id.county_id.code,
							'distrito': partner_id.district_id.code,
							'barrio': partner_id.neighborhood_id.code,
							'sennas': partner_id.street[:159],
						},
						'correo_electronico': partner_id.get_main_email(),
					},
				}

			else:
				emisor = {
					'emisor': {
						'nombre': inv.company_id.name[:99],
						'identificacion': {
							'tipo': inv.company_id.identification_id.code,
							'numero': inv.company_id.vat,
						},
						'nombre_comercial': inv.company_id.commercial_name or '',
						'ubicacion': {
							'provincia': inv.company_id.state_id.fe_code,
							'canton': inv.company_id.county_id.code,
							'distrito': inv.company_id.district_id.code,
							'barrio': inv.company_id.neighborhood_id.code,
							'sennas': inv.company_id.street[:159],
						},
						'telefono': {
							'cod_pais': inv.company_id.phone_code,
							'numero': inv.company_id.get_valid_phone(),
						},
						'fax': {
							'cod_pais': inv.company_id.fax_code,
							'numero': inv.company_id.get_valid_fax(),
						},
						'correo_electronico': inv.company_id.email,
					},
				}
				receptor = {
					'receptor': {
						'nombre': partner_id.name[:99],
						'identificacion': receptor_identificacion,
						'IdentificacionExtranjero': receptor_identificacion_extranjero,
						'correo_electronico': partner_id.get_main_email(),
					},
				}

			otros_cargos_list = list()
			for code, value in otros_cargos.items():
				otros_cargos_dic = {
					'tipodocumento': code,
					'detalle': value['name'],
					'montocargo': str(standard_tools.round_decimal(value['total'], 5)),
				}
				if value['rate'] != 0:
					otros_cargos_dic.update(porcentaje=standard_tools.round_decimal(value['rate'] / 100, 5))

				otros_cargos_list.append(otros_cargos_dic)
				total_otros_cargos += value['total']
			total_otros_cargos = standard_tools.round_decimal(total_otros_cargos, 5)

			if inv.invoice_date_due:
				plazo_credito = (inv.invoice_date_due - inv.invoice_date).days
			else:
				plazo_credito = inv.invoice_payment_term_id.line_ids and inv.invoice_payment_term_id.line_ids[0].days or 0

			if inv.invoice_payment_term_id.sale_conditions_id:
				condicion_venta = inv.invoice_payment_term_id.sale_conditions_id.sequence
			else:
				condicion_venta = plazo_credito == 0 and '01' or '02'

			payload = {
				'api_key': inv.company_id.api_key,
				'clave': {
					'sucursal': inv.journal_id.sucursal,  # Se agrega la sucursal 001
					'terminal': inv.journal_id.terminal,  # Se agrega la terminal 00001
					'tipo': type_document,
					'comprobante': inv.name[10:],
					'pais': '506',
					'dia': '%02d' % now_cr.day,
					'mes': '%02d' % now_cr.month,
					'anno': str(now_cr.year)[2:4],
					'situacion_presentacion': inv.number_electronic[41],
					'codigo_seguridad': inv.number_electronic[42:],
				},
				'encabezado': {
					'codigo_actividad': inv.activity_type.code,
					'fecha': inv.date_issuance,
					'condicion_venta': condicion_venta,
					'plazo_credito': plazo_credito,
					'medio_pago': medio_pago,
				},
				'detalle': lines,
				'otroscargos': otros_cargos_list,
				'resumen': {
					'moneda': inv.currency_id.name,
					'tipo_cambio': standard_tools.round_decimal(inv.currency_rate_save, 5),
					'totalserviciogravado': standard_tools.round_decimal(totalserviciogravado, 5),
					'totalservicioexento': standard_tools.round_decimal(totalservicioexento, 5),
					'totalmercaderiagravado': standard_tools.round_decimal(totalmercaderiagravado, 5),
					'totalmercaderiaexento': standard_tools.round_decimal(totalmercaderiaexento, 5),
					'totalgravado': standard_tools.round_decimal(totalserviciogravado + totalmercaderiagravado, 5),
					'totalexento': standard_tools.round_decimal(totalservicioexento + totalmercaderiaexento, 5),
					'totalventa': standard_tools.round_decimal(totalserviciogravado + totalmercaderiagravado + totalservicioexento + totalmercaderiaexento + totalservexonerado + totalmercexonerada, 5),
					'totaldescuentos': standard_tools.round_decimal(resumen_total_discount, 5) or '',
					'totalventaneta': standard_tools.round_decimal((totalserviciogravado + totalmercaderiagravado + totalservicioexento + totalmercaderiaexento + totalservexonerado + totalmercexonerada) - resumen_total_discount, 5),
					'totalimpuestos': standard_tools.round_decimal(impuestos_total - total_exoneracion, 5),
					'totalotroscargos': total_otros_cargos or '',
					'totalcomprobante': standard_tools.round_decimal(totalcomprobante - resumen_total_discount + impuestos_total - total_exoneracion - total_iva_devuelto + total_otros_cargos, 5),
				},
				'referencia': referencia,
				'otros': [{
					'codigo': '',
					'texto': 'Generado por www.delfixcr.com con el sistema Odoo.',
					'contenido': ''
				}],
			}

			otros = payload['otros']
			for special_tag in inv.special_tags_lines:
				if special_tag.element == 'CompraEntrega':
					if 'compra_entrega' not in payload:
						payload.update({
							'compra_entrega': {}
						})
					payload.get('compra_entrega').update({
						special_tag.code: str(special_tag.content),
					})
				elif special_tag.content:
					body = {
						'codigo': special_tag.code or '',
						'texto': str(special_tag.content),
						'contenido': ''
					}
					otros.append(body)

			if type_document != '09':
				payload.get('resumen').update({
					'totalservicioexonerado': standard_tools.round_decimal(totalservexonerado, 5),
					'totalmercaderiaexonerado': standard_tools.round_decimal(totalmercexonerada, 5),
					'totalexonerado': standard_tools.round_decimal(totalservexonerado + totalmercexonerada, 5),
				})
				if type_document != '08':
					payload.get('resumen').update({
						'totalivadevuelto': standard_tools.round_decimal(total_iva_devuelto, 5),
					})

			payload.update(emisor)
			payload.update(receptor)

			return payload

	# Envia el payload de la factura a MH
	def _send_invoice(self, config, inv, payload):

		if config.mode_debug:
			_logger.info('\n---------------------------------\nDatos a enviar a MH ' + str(payload) + '\n---------------------------------\n')

		if inv.company_id.frm_ws_ambiente == 'stag':
			requests_url = 'https://www.comprobanteselectronicoscr.com/api/makeXML.stag.43'
		else:
			requests_url = 'https://www.comprobanteselectronicoscr.com/api/makeXML.prod.43'

		response_content = ''
		# Si no se puede establecer conexion con hacienda se pone el estado conexion_error
		try:
			if config.mode_debug:
				_logger.info('\n---------------------------------\nEnviando la Factura: \n' + str(inv.name) + '\n---------------------------------\n')
			response_document = requests.post(requests_url, data=json.dumps(payload))
			response_content = json.loads(str(response_document._content, 'utf-8'))
			# Si hacienda devuelve respuesta como errores se guarda el error en electronic_invoice_return_message
			try:
				if response_document.status_code == 200:
					if response_content.get('code'):
						if config.mode_debug:
							_logger.info('\n---------------------------------\nContenido de la respuesta' + str(response_content) + '\n---------------------------------\n')
							_logger.info('\n---------------------------------\nCodigo: ' + str(response_content.get('code')) + '\n---------------------------------\n')
						if str(response_content.get('code')) in ('1', '43'):
							inv.number_electronic = response_content.get('clave')
							if config.mode_debug:
								_logger.info('\n---------------------------------\nRespuesta MH, numero electronico: \n' + str(response_content.get('clave')) + '\n---------------------------------\n')

							if response_content.get('data'):
								inv.fname_xml_comprobante = self.get_type_name_pdf(inv) + inv.number_electronic + '.xml'
								self.env['ir.attachment'].create({
									'name': inv.fname_xml_comprobante,
									'type': 'binary',
									'datas': response_content.get('data'),
									'res_model': inv._name,
									'res_id': inv.id,
									'res_field': 'xml_comprobante',
									'mimetype': 'application/xml'
								})
								inv.electronic_invoice_return_message = False
								inv.state_tributacion = 'enviado'
						else:
							inv.electronic_invoice_return_message = 'Error Respuesta de MH: ' + str(response_content)
							inv.state_tributacion = 'enviado_error'
							if config.mode_debug:
								_logger.info('\n---------------------------------\nError de FE: \n' + 'Error Respuesta de MH: ' + str(response_content) + '\n' + ' Error interno de odoo: ' + str(sys.exc_info()) + '\n---------------------------------\n')
				else:
					inv.electronic_invoice_return_message = 'Error Respuesta de MH: ' + str(response_content)
					inv.state_tributacion = 'enviado_error'
					if config.mode_debug:
						_logger.info('\n---------------------------------\nError de FE: \n' + 'Error Respuesta de MH: ' + str(response_content) + '\n' + ' Error interno de odoo: ' + str(sys.exc_info()) + '\n---------------------------------\n')

			except:
				if config.mode_debug:
					_logger.info('\n---------------------------------\nError de FE: \n' + 'Error Respuesta de MH: ' + str(response_content) + '\n' + ' Error interno de odoo: ' + str(sys.exc_info()) + '\n---------------------------------\n')
				inv.electronic_invoice_return_message = 'Error Respuesta de MH: ' + str(response_content) + '\n' + ' Error interno de odoo: ' + str(sys.exc_info())
				inv.state_tributacion = 'enviado_error'
		except:
			if config.mode_debug:
				_logger.info('\n---------------------------------\nError de FE: \n' + str(sys.exc_info()) + '\n---------------------------------\n')
			inv.electronic_invoice_return_message = 'Error interno de odoo: ' + str(sys.exc_info())  # Obtiene errores de python
			inv.state_tributacion = 'conexion_error'

	# Override
	def action_send_and_print(self):
		# El método Original provoca un BUG con los adjuntos y los mescla entre facturas

		invoices = self.env['account.move'].search([
			('id', 'in', self.ids),
			('state_tributacion', '=', 'aceptado'),
		])

		for inv in invoices:
			inv.send_email_out_invoice(inv, manual_send=True)

		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': 'Correo Electrónico',
				'message': 'Facturas con estado "Aceptado" fueron enviadas ',
				'sticky': False,
			}
		}

	def action_debit_note(self):
		action = self.sudo().env.ref('cr_electronic_invoice.action_debit_note_wizard').read()[0]
		return action

	def action_cancel_invoice_rejected(self):
		if self.state_tributacion == 'rechazado' and self.state == 'posted':
			self.button_draft()
			self.button_cancel()

	def _get_sequence_electronic(self):
		if self.type_document == '01':
			sequence_id = self.journal_id.electronic_invoice_sequence_id
		elif self.type_document == '02':
			sequence_id = self.journal_id.debit_note_sequence_id
		elif self.type_document == '03':
			sequence_id = self.journal_id.credit_note_sequence_id
		elif self.type_document == '04':
			sequence_id = self.journal_id.ticket_sequence_id
		elif self.type_document == '08':
			sequence_id = self.journal_id.purchase_invoice_sequence_id
		elif self.type_document == '09':
			sequence_id = self.journal_id.export_invoice_sequence_id

		if sequence_id:
			return str(self.journal_id.sucursal) + str(self.journal_id.terminal) + str(self.type_document) + sequence_id.next_by_id()
		else:
			return ''

	# Overrride, se modifica dominio para ignorar FE
	def _get_last_sequence_domain(self, relaxed=False):
		self.ensure_one()
		if not self.date or not self.journal_id:
			return "WHERE FALSE", {}
		where_string = "WHERE journal_id = %(journal_id)s AND name != '/'"
		param = {'journal_id': self.journal_id.id}

		if not relaxed:
			domain = [('journal_id', '=', self.journal_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]

			# Se indica que ignore las secuencias de FE
			domain.append(('number_electronic', '=', False))

			if self.journal_id.refund_sequence:
				refund_types = ('out_refund', 'in_refund')
				domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
			reference_move_name = self.search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
			if not reference_move_name:
				reference_move_name = self.search(domain, order='date asc', limit=1).name
			sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
			if sequence_number_reset == 'year':
				where_string += " AND date_trunc('year', date::timestamp without time zone) = date_trunc('year', %(date)s) "
				param['date'] = self.date
				param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
			elif sequence_number_reset == 'month':
				where_string += " AND date_trunc('month', date::timestamp without time zone) = date_trunc('month', %(date)s) "
				param['date'] = self.date
			else:
				param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

			if param.get('anti_regex') and not self.journal_id.sequence_override_regex:
				where_string += " AND sequence_prefix !~ %(anti_regex)s "

		if self.journal_id.refund_sequence:
			if self.move_type in ('out_refund', 'in_refund'):
				where_string += " AND move_type IN ('out_refund', 'in_refund') "
			else:
				where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "

		# Se indica que ignore las secuencias de FE
		where_string += " AND number_electronic IS NULL "

		return where_string, param

	def _get_last_sequence(self, **kwargs):
		if self.type_document not in ('05', '') and self.company_id.frm_ws_ambiente != 'disabled':
			return '/'
		# Metodo diferente entre versiones de Odoo 15
		# Se agrega compatibilidad de atributos se agrega **kwargs para soportar _get_last_sequence(relaxed=relaxed) o _get_last_sequence(relaxed=False, with_prefix=None, lock=True)
		return super(AccountInvoiceElectronic, self)._get_last_sequence(**kwargs)

	@api.model
	def create(self, values):
		inv = super(AccountInvoiceElectronic, self).create(values)

		if inv.partner_id:
			if not inv.payment_methods_id and inv.partner_id.payment_methods_id:
				inv.payment_methods_id = inv.partner_id.payment_methods_id

			if inv.move_type == 'out_invoice':
				if not inv.type_document_selection and inv.partner_id.export_invoice:
					inv.type_document_selection = self.env['type.document.selection'].search([('code', '=', '09')], limit=1)

			if inv.move_type == 'in_invoice':
				if not inv.type_document_selection and inv.partner_id.purchase_invoice:
					inv.activity_type = inv.partner_id.activity_type
					inv.type_document_selection = self.env['type.document.selection'].search([('code', '=', '08')], limit=1)
		return inv

	def action_switch_invoice_into_refund_credit_note(self):

		if any(inv.state_tributacion is not False or inv.state_send_invoice is not False for inv in self):
			raise UserError('Acción no permitida: El documento electrónico se encuentra validado')

		return super(AccountInvoiceElectronic, self).action_switch_invoice_into_refund_credit_note()
