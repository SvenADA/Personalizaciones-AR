# -*- coding: utf-8 -*-
##############################################################################
#	Odoo Proprietary License v1.0
#	Copyright (c) 2019 Delfix Tecnosoluciones S.A. (http://www.delfixcr.com) All Rights Reserved.
##############################################################################
import json
import requests
import logging
from odoo import models, fields, api, _
import pytz
import base64
from datetime import datetime
import random
import sys
import tempfile
import os
from xml.dom import minidom
import subprocess
from odoo.addons.cr_electronic_invoice.models import standard_tools

_logger = logging.getLogger(__name__)

try:
	# Importacion de firmador por python
	import xmlsig
	from ..signer.xades_python.context2 import XAdESContext2, PolicyId2, create_xades_epes_signature
	from OpenSSL import crypto
	from lxml import etree
except ImportError:
	_logger.warning('Librería opcional faltante para firmar facturas con Python, utilizar pip3 install xmlsig')


headers = {
	"01": """<FacturaElectronica 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
		xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica FacturaElectronica_V4.3.xsd">""",

	"02": """<NotaDebitoElectronica 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaDebitoElectronica" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
		xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaDebitoElectronica NotaDebitoElectronica_V4.3.xsd">""",

	"03": """<NotaCreditoElectronica 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaCreditoElectronica" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
		xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaCreditoElectronica NotaCreditoElectronica_V4.3.xsd">""",

	"04": """<TiqueteElectronico 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronico" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
		xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronico TiqueteElectronico_V4.3.xsd">""",

	"05": """<MensajeReceptor 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeReceptor" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeReceptor MensajeReceptor_V4.3.xsd">""",

	"08": """<FacturaElectronicaCompra 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaCompra" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
		xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaCompra FacturaElectronicaCompra_V4.3.xsd">""",

	"09": """<FacturaElectronicaExportacion 
		xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaExportacion" 
		xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
		xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
		xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
		xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaExportacion FacturaElectronicaExportacion_V4.3.xsd">""",

}

end_headers = {
	"01": """</FacturaElectronica>""",

	"02": """</NotaDebitoElectronica>""",

	"03": """</NotaCreditoElectronica>""",

	"04": """</TiqueteElectronico>""",

	"05": """</MensajeReceptor>""",

	"08": """</FacturaElectronicaCompra>""",

	"09": """</FacturaElectronicaExportacion>""",
}


class AccountInvoiceElectronicMH(models.Model):
	_inherit = "account.move"

	# Hereda del metodo de FE original
	def _process_comprobante(self, comprobantes, config):
		if config.connection_mode in ('direct', 'direct_python'):
			for comprobante in comprobantes:
				if comprobante.company_id.frm_ws_ambiente != 'disabled':
					xml, data_to_send = self._get_xml_receptor(comprobante, config)

					if not comprobante.xml_comprobante:
						xml_sign = self._sign_document(xml, comprobante, config)
						# Si devuelve falso el xml firmado no se pudo crear
						if xml_sign == False:
							comprobante.state_tributacion = 'enviado_error'
							continue

						# Los dos firmados devuelve tipo de datos distintos
						if type(xml_sign) is str:
							xml_sign = xml_sign.encode('utf-8')

						xml_base64 = base64.b64encode(xml_sign)
						comprobante.fname_xml_comprobante = 'ARC-' + comprobante.number_electronic_supplier + '.xml'
						self.env['ir.attachment'].create({
							'name': comprobante.fname_xml_comprobante,
							'type': 'binary',
							'datas': xml_base64,
							'res_model': comprobante._name,
							'res_id': comprobante.id,
							'res_field': 'xml_comprobante',
							'mimetype': 'application/xml'
						})
					else:
						xml_base64 = comprobante.xml_comprobante

					data_to_send.update(comprobanteXml=xml_base64.decode('utf-8'))
					self._send_xml_mh(config, comprobante, data_to_send)
					if comprobante.invoice_id:
						comprobante.invoice_id.state_send_invoice = comprobante.state_tributacion
		else:
			return super(AccountInvoiceElectronicMH, self)._process_comprobante(comprobantes, config)

	def _get_xml_receptor(self, comprobante, config):
		root = standard_tools.xml_supplier_to_ET(comprobante.xml_supplier_approval)

		total_impuesto = ''
		if (root.findall('ResumenFactura') and root.findall('ResumenFactura')[0].findall('TotalImpuesto')):
			total_impuesto = '<MontoTotalImpuesto>' + root.findall('ResumenFactura')[0].findall('TotalImpuesto')[0].text + '</MontoTotalImpuesto>'

		monto_total_impuesto_acreditar = ''
		monto_total_deGasto_aplicable = ''
		if comprobante.iva_condition_id.code != '05' and comprobante.state_invoice_partner != '3':
			monto_total_impuesto_acreditar = """<MontoTotalImpuestoAcreditar>""" + str(comprobante.accredit_tax) + """</MontoTotalImpuestoAcreditar>"""
			monto_total_deGasto_aplicable = """<MontoTotalDeGastoAplicable>""" + str(comprobante.applicable_expenditure) + """</MontoTotalDeGastoAplicable>"""

		codigo_actividad = ''
		if comprobante.iva_condition_id.code != '05':
			codigo_actividad = """<CodigoActividad>""" + str(comprobante.activity_type.code) + """</CodigoActividad>"""

		condicion_impuesto = ''
		if comprobante.state_invoice_partner != '3':
			condicion_impuesto = """<CondicionImpuesto>""" + str(comprobante.iva_condition_id.code) + """</CondicionImpuesto>"""

		if comprobante.state_invoice_partner == '1':
			detalle_mensaje = 'Aceptado'
		else:
			detalle_mensaje = str(comprobante.reason_rejection)

		# Se genera el codigo de seguridad aleatorio
		security_code = ''
		for i in range(8):
			security_code += str(random.randint(0, 9))

		# Se forma el nuemro de 50 digitos
		if not comprobante.number_electronic_supplier:
			now_cr = datetime.strptime(comprobante.date_issuance_receiver, "%Y-%m-%dT%H:%M:%S-06:00")
			number_50_digits = '506'  # Codigo pais
			number_50_digits += ('0' + str(now_cr.day))[-2:]  # dia 01
			number_50_digits += ('0' + str(now_cr.month))[-2:]  # mes 01
			number_50_digits += str(now_cr.year)[2:4]  # anno 18
			number_50_digits += ('0000' + comprobante.company_id.vat)[-12:]  # cedula empresa
			number_50_digits += comprobante.consecutive_number_receiver  # Numero de factura de 20 digitos
			number_50_digits += '1'  # Estado de envio
			number_50_digits += security_code  # Codigo de seguridad
			comprobante.number_electronic_supplier = number_50_digits + '-' + comprobante.consecutive_number_receiver

		xml = """<?xml version="1.0" encoding="UTF-8"?>"""

		xml += headers['05']

		xml += """
				  <Clave>""" + root.findall('Clave')[0].text + """</Clave>
				  <NumeroCedulaEmisor>""" + root.findall('Emisor')[0].findall('Identificacion')[0].findall('Numero')[0].text + """</NumeroCedulaEmisor>
				  <FechaEmisionDoc>""" + comprobante.date_issuance_receiver + """</FechaEmisionDoc>
				  <Mensaje>""" + comprobante.state_invoice_partner + """</Mensaje>
				  <DetalleMensaje>""" + detalle_mensaje[:159] + """</DetalleMensaje>
					""" + total_impuesto + """
				  """ + codigo_actividad + """
				  """ + condicion_impuesto + """
				  """ + monto_total_impuesto_acreditar + """
				  """ + monto_total_deGasto_aplicable + """
				  <TotalFactura>""" + root.findall('ResumenFactura')[0].findall('TotalComprobante')[0].text + """</TotalFactura>
				  <NumeroCedulaReceptor>""" + comprobante.company_id.vat + """</NumeroCedulaReceptor>
				  <NumeroConsecutivoReceptor>""" + comprobante.consecutive_number_receiver + """</NumeroConsecutivoReceptor>
				"""
		xml += end_headers['05']
		xml_format = minidom.parseString(xml)
		xml = xml_format.toprettyxml()
		xml = os.linesep.join([s for s in xml.splitlines() if s.strip()])

		if config.mode_debug:
			_logger.info('\n---------------------------------\nXML creado ' + str(xml) + '\n---------------------------------\n')

		data_to_send = {
			"fecha": comprobante.date_issuance_receiver,
			"clave": comprobante.number_electronic_supplier[:50],
			"emisor": {
				"tipoIdentificacion": str(root.findall('Emisor')[0].findall('Identificacion')[0].findall('Tipo')[0].text),
				"numeroIdentificacion": str(root.findall('Emisor')[0].findall('Identificacion')[0].findall('Numero')[0].text)
			},
			"receptor": {
				"tipoIdentificacion": str(comprobante.company_id.identification_id.code),
				"numeroIdentificacion": str(comprobante.company_id.vat)
			},
			"consecutivoReceptor": comprobante.consecutive_number_receiver,
		}
		if config.mode_debug:
			_logger.info('\n---------------------------------\nXML creado: ' + str(xml) + '\n---------------------------------\n')

		return xml, data_to_send

	# Se hereda el metodo original de FE
	def _consult(self, inv, number, config):
		if config.connection_mode in ('direct', 'direct_python'):
			self._consult_mh(inv, number, config)
		else:
			return super(AccountInvoiceElectronicMH, self)._consult(inv, number, config)

	def _consult_mh(self, inv, number, config):
		if config.mode_debug:
			_logger.info('\n---------------------------------\nConsultando id : modelo ' + str(inv.id) + ' : ' + str(inv._name) + '\n---------------------------------\n')
			_logger.info('\n---------------------------------\nNumero a consultar ' + str(number) + '\n---------------------------------\n')

		if inv.company_id.frm_ws_ambiente == 'stag':
			environment = "recepcion-sandbox"
		else:
			environment = "recepcion"

		token = inv.company_id.get_token_temp()

		headers = {'Content-type': 'application/json;charset=UTF-8', 'Authorization': token}

		requests_url = 'https://api.comprobanteselectronicos.go.cr/' + environment + '/v1/recepcion/' + number

		try:
			response_document = requests.get(requests_url, headers=headers)
			if config.mode_debug:
				_logger.info('\n---------------------------------\n' + 'Codigo de respuesta: ' + str(response_document.status_code) + '\n---------------------------------\n')
			if response_document.status_code == 200:
				response_content = response_document.json()
				if response_content.get('ind-estado', False):
					inv.state_tributacion = response_content.get('ind-estado')
					if inv.state_tributacion in ('aceptado', 'rechazado'):
						# Direntes modelos y campo
						if (inv._name == 'account.move') or inv._name == 'pos.order':
							inv.fname_xml_respuesta_tributacion = 'AHC-' + number + '.xml'
						else:
							inv.fname_xml_respuesta_tributacion = 'AHR-' + number + '.xml'
						# inv.xml_respuesta_tributacion = response_content.get('respuesta-xml')
						xml_response = response_content.get('respuesta-xml')
						self.env['ir.attachment'].create({
							'name': inv.fname_xml_respuesta_tributacion,
							'type': 'binary',
							'datas': xml_response,
							'res_model': inv._name,
							'res_id': inv.id,
							'res_field': 'xml_respuesta_tributacion',
							'mimetype': 'application/xml'
						})
						root = standard_tools.xml_supplier_to_ET(xml_response)
						if root.findall('DetalleMensaje')[0].text != ' ':
							detalle = root.findall('DetalleMensaje')[0].text
						else:
							detalle = False
						inv.electronic_invoice_return_message = detalle
						if inv.state_tributacion == 'rechazado':
							state_temp = False
							if detalle.find("La firma del comprobante electrónico no es válida") >= 0:
								state_temp = 'validating_signature'
							if detalle.find("Rechazado, valorar reenvío.") >= 0:
								state_temp = 'esperando'

							if state_temp:
								now_utc = datetime.now(pytz.timezone('UTC'))
								date_now = now_utc.astimezone(pytz.timezone('America/Costa_Rica')).date()

								if inv._name == 'electronic.voucher.supplier':
									obj_date = inv.validate_date
								else:
									obj_date = datetime.strptime(inv.date_issuance, "%Y-%m-%dT%H:%M:%S-06:00").date()
								if abs(obj_date - date_now).days >= 3:
									inv.state_tributacion = 'rechazado'
								else:
									inv.state_tributacion = state_temp
					if config.mode_debug:
						_logger.info('\n---------------------------------\nDocumento: ' + str(response_content.get('ind-estado')) + '\n---------------------------------\n')
				else:
					inv.electronic_invoice_return_message = 'Error de MH consultando el documento: \n' + str(response_content)
					inv.state_tributacion = 'consultar_error'
			elif response_document.status_code == 401:
				# Se deja el estado El token expiro
				pass
			elif response_document.status_code == 400:
				inv.electronic_invoice_return_message = response_document.headers.get('X-Error-Cause')
				inv.state_tributacion = 'consultar_error'
			elif response_document.status_code == 404:
				inv.electronic_invoice_return_message = response_document.headers.get('X-Error-Cause')
				inv.state_tributacion = 'error'
			elif response_document.status_code == 503:
				# Se deja el estado, el servidor está saturado en ese momento
				pass
			else:
				inv.state_tributacion = 'consultar_error'
				inv.electronic_invoice_return_message = str(response_document, 'utf-8')
		except:
			if config.mode_debug:
				_logger.info('\n---------------------------------\nError de FE: \n' + str(sys.exc_info()) + '\n---------------------------------\n')
			inv.electronic_invoice_return_message = 'Error interno de odoo: ' + str(sys.exc_info())  # Obtiene errores de python
			inv.state_tributacion = 'consultar_error'

	# Hereda del metodo de FE original
	# Itera las factura y se plican sus respectivos metodos
	def _process_invoices(self, config, invoices):
		if config.connection_mode in ('direct', 'direct_python'):
			for inv in invoices:
				xml, data_to_send = self._create_xml(config, inv)

				if not inv.xml_comprobante:
					xml_sign = self._sign_document(xml, inv, config)
					# Si devuelve falso el xml firmado no se pudo crear
					if xml_sign == False:
						inv.state_tributacion = 'enviado_error'
						continue

					# Los dos firmados devuelve tipo de datos distintos
					if type(xml_sign) is str:
						xml_sign = xml_sign.encode('utf-8')

					xml_base64 = base64.b64encode(xml_sign)
					inv.fname_xml_comprobante = self.get_type_name_pdf(inv) + inv.number_electronic + '.xml'
					self.env['ir.attachment'].create({
						'name': inv.fname_xml_comprobante,
						'type': 'binary',
						'datas': xml_base64,
						'res_model': inv._name,
						'res_id': inv.id,
						'res_field': 'xml_comprobante',
						'mimetype': 'application/xml'
					})
				else:
					xml_base64 = inv.xml_comprobante

				data_to_send.update(comprobanteXml=xml_base64.decode('utf-8'))
				self._send_xml_mh(config, inv, data_to_send)
		else:
			return super(AccountInvoiceElectronicMH, self)._process_invoices(config, invoices)

	# Forma la estructura XML de la factura
	def _create_xml(self, config, inv):
		if inv.company_id.frm_ws_ambiente != 'disabled':

			if config.mode_debug:
				_logger.info('\n---------------------------------\nProcesando la factura id : numero ' + str(inv.id) + ' : ' + str(inv.name) + '\n---------------------------------\n')

			type_document = inv.type_document
			informacion_referencia = ''
			medio_pago = (inv.payment_methods_id and inv.payment_methods_id.sequence) or '01'
			export_invoice_reference = False

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
				informacion_referencia += """
				<InformacionReferencia>
					<TipoDoc>""" + str(tipo_documento_referencia) + """</TipoDoc>
					<Numero>""" + str(numero_documento_referencia) + """</Numero>
					<FechaEmision>""" + str(fecha_emision_referencia) + """</FechaEmision>
					<Codigo>""" + str(codigo_referencia) + """</Codigo>
					<Razon>""" + str(razon_referencia) + """</Razon>
				</InformacionReferencia>
				"""
				if reference_document.invoice_id.type_document == '09':
					export_invoice_reference = True

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

				informacion_referencia += """
				<InformacionReferencia>
					<TipoDoc>""" + str(tipo_documento_referencia) + """</TipoDoc>
					<Numero>""" + str(numero_documento_referencia) + """</Numero>
					<FechaEmision>""" + str(fecha_emision_referencia) + """</FechaEmision>
					<Codigo>""" + str(codigo_referencia) + """</Codigo>
					<Razon>""" + str(razon_referencia) + """</Razon>
				</InformacionReferencia>
				"""

			detail_lines = ''
			numero = 0

			# Valida si el cliente esta ligado a una empresa si es asi, se factura en nombre de la empresa
			partner_id = self.get_partner_to_ei(inv)

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
					impuestos = ''
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

							exoneracion = ''
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
									exoneracion = """
									<Exoneracion>
										<TipoDocumento>""" + str(doc_exoneration.document_type_id.code) + """</TipoDocumento>
										<NumeroDocumento>""" + str(doc_exoneration.document_number) + """</NumeroDocumento>
										<NombreInstitucion>""" + str(doc_exoneration.institution_name) + """</NombreInstitucion>
										<FechaEmision>""" + str(doc_exoneration.date_issue) + "T" + doc_exoneration.time_issue + "-06:00" + """</FechaEmision>
										<PorcentajeExoneracion>""" + str(purchase_percentage) + """</PorcentajeExoneracion>
										<MontoExoneracion>""" + str(montoimpuesto) + """</MontoExoneracion>
									</Exoneracion>
									"""

							if tax_id.tax_type.code == '01':
								impuesto_num = standard_tools.round_decimal(((quantity_line * discont_apli) + impuestos_acumulados) * ((tax_id.amount or 0.0) / 100.0), 5)
								iva_acumulado += impuesto_num
							else:
								impuesto_num = standard_tools.round_decimal(quantity_line * discont_apli * ((tax_id.amount or 0.0) / 100.0), 5)

							if tax_id.tax_type and tax_id.tax_type.code != '00':
								moto_exportacion = ''
								if type_document == '09' or export_invoice_reference:
									moto_exportacion = """<MontoExportacion>""" + str(impuesto_num) + """</MontoExportacion>"""

								codigo_tarifa = ""
								if tax_id.tax_rate:
									codigo_tarifa = """<CodigoTarifa>""" + str(tax_id.tax_rate.code) + """</CodigoTarifa>"""

								impuestos += """
								<Impuesto>
									<Codigo>""" + str(tax_id.tax_type.code) + """</Codigo>
									""" + codigo_tarifa + """
									<Tarifa>""" + str(tax_id.amount) + """</Tarifa>
									<Monto>""" + str(impuesto_num) + """</Monto>
									""" + moto_exportacion + """
									""" + exoneracion + """
								</Impuesto>"""

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
										'name': tax_id.name,
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

						unidad_comercial = ''
						if inv_line.product_id.commercial_measurement:
							unidad_comercial = "<UnidadMedidaComercial>" + str(inv_line.product_id.commercial_measurement)[:20] + "</UnidadMedidaComercial>"
						discount = ''
						if inv_line.discount:
							discount = """
							<Descuento>
								<MontoDescuento>""" + str(discount_line) + """</MontoDescuento>
								<NaturalezaDescuento>""" + str(discount_note_tmp) + """</NaturalezaDescuento>
							</Descuento>
							"""
						# Factura de  exportacion
						partida_arancelaria = ''
						if inv_line.product_id.tariff_item and (type_document == '09' or export_invoice_reference):
							partida_arancelaria = """<PartidaArancelaria>""" + str(inv_line.product_id.tariff_item) + """</PartidaArancelaria>"""

						impuesto_neto = standard_tools.round_decimal(iva_acumulado - total_exoneracion_line, 5)

						cabys_code_str = ''
						cabys_code = inv_line.product_id.get_cabys_code()
						if cabys_code:
							cabys_code_str = "<Codigo>" + str(cabys_code) + "</Codigo>"

						detail_lines += """
						<LineaDetalle>
							<NumeroLinea>""" + str(numero) + """</NumeroLinea>
							""" + partida_arancelaria + """
							""" + cabys_code_str + """
							<CodigoComercial>
								<Tipo>""" + str(inv_line.product_id.code_type_id.code or '04') + """</Tipo>
								<Codigo>""" + str((inv_line.product_id.default_code and str(inv_line.product_id.default_code)[:20]) or '000') + """</Codigo>
							</CodigoComercial>
							<Cantidad>""" + str(quantity_line) + """</Cantidad>
							<UnidadMedida>""" + str(inv_line.product_uom_id.code or 'Sp') + """</UnidadMedida>
							""" + unidad_comercial + """
							<Detalle>""" + standard_tools.replace_invalid_tokens(inv_line.name[:199]) + """</Detalle>
							<PrecioUnitario>""" + str(price_unit_line) + """</PrecioUnitario>
							<MontoTotal>""" + str(standard_tools.round_decimal(sud_total, 5)) + """</MontoTotal>
							""" + discount + """
							<SubTotal>""" + str(standard_tools.round_decimal(sud_total - discount_line, 5)) + """</SubTotal>
							""" + impuestos + """
							<ImpuestoNeto>""" + str(impuesto_neto) + """</ImpuestoNeto>
							<MontoTotalLinea>""" + str(standard_tools.round_decimal(sud_total - discount_line + impuestos_acumulados - total_exoneracion_line, 5)) + """</MontoTotalLinea>
						</LineaDetalle>"""

						# Se suma el impuesto cuando el es un servico de salud
						if inv.company_id.health_service and inv_line.product_id.type == 'service' and inv_line.product_id.return_iva and medio_pago == '02':
							total_iva_devuelto += impuesto_neto

			total_decuento = ''
			if resumen_total_discount:
				total_decuento = "<TotalDescuentos>" + str(standard_tools.round_decimal(resumen_total_discount, 5) or '') + "</TotalDescuentos>"

			identificacion = ''
			if partner_id.identification_id and partner_id.ref:
				if partner_id.identification_id.code == '05':
					identificacion = "<IdentificacionExtranjero>" + str(partner_id.ref) + "</IdentificacionExtranjero>"
				else:
					identificacion = """<Identificacion>
						<Tipo>""" + str(partner_id.identification_id.code) + """</Tipo>
						<Numero>""" + str(partner_id.ref) + """</Numero>
					</Identificacion>"""

			# if type_document != '09':
			# 	ubicacion = 

			correo_electronico = ""
			main_email = partner_id.get_main_email()
			if main_email:
				correo_electronico = "<CorreoElectronico>" + main_email + "</CorreoElectronico>"
			fax = ''
			if inv.company_id.fax:
				fax = """
				<Fax>
					<CodigoPais>""" + inv.company_id.fax_code + """</CodigoPais>
					<NumTelefono>""" + inv.company_id.get_valid_fax() + """</NumTelefono>
				</Fax>"""
			barrio = ''
			if inv.company_id.neighborhood_id:
				barrio = '<Barrio>' + str(inv.company_id.neighborhood_id.code) + '</Barrio>'

			# todo OtrasSenasExtranjero

			nombre_comercial = ''
			if inv.company_id.commercial_name:
				nombre_comercial = """<NombreComercial>""" + standard_tools.replace_invalid_tokens(str(inv.company_id.commercial_name)[:80]) + """</NombreComercial>"""

			data_company = """
							<Nombre>""" + standard_tools.replace_invalid_tokens(str(inv.company_id.name)[:99]) + """</Nombre>
							<Identificacion>
								<Tipo>""" + str(inv.company_id.identification_id.code) + """</Tipo>
								<Numero>""" + str(inv.company_id.vat) + """</Numero>
							</Identificacion>
							""" + nombre_comercial + """
							<Ubicacion>
							  <Provincia>""" + str(inv.company_id.state_id.fe_code) + """</Provincia>
							  <Canton>""" + str(inv.company_id.county_id.code) + """</Canton>
							  <Distrito>""" + str(inv.company_id.district_id.code) + """</Distrito>
							  """ + barrio + """
							  <OtrasSenas>""" + standard_tools.replace_invalid_tokens(str(inv.company_id.street)[:159]) + """</OtrasSenas>
							</Ubicacion>
							<Telefono>
								<CodigoPais>""" + str(inv.company_id.phone_code) + """</CodigoPais>
								<NumTelefono>""" + inv.company_id.get_valid_phone() + """</NumTelefono>
							</Telefono>
							 """ + fax + """
							<CorreoElectronico>""" + str(inv.company_id.email) + """</CorreoElectronico>
						"""

			# Cambio de receptor y emisor para la factura de compra
			# Se cambia entre el emisor y el receptor
			if type_document == '08':
				receptor = """
						<Receptor>
							""" + data_company + """
						</Receptor>"""

				barrio = ''
				if partner_id.neighborhood_id:
					barrio = '<Barrio>' + str(partner_id.neighborhood_id.code) + '</Barrio>'

				emisor = """
						<Emisor>
							<Nombre>""" + standard_tools.replace_invalid_tokens(str(partner_id.name)[:99]) + """</Nombre>
							""" + identificacion + """
							<Ubicacion>
							  <Provincia>""" + str(partner_id.state_id.fe_code) + """</Provincia>
							  <Canton>""" + str(partner_id.county_id.code) + """</Canton>
							  <Distrito>""" + str(partner_id.district_id.code) + """</Distrito>
							  """ + barrio + """
							  <OtrasSenas>""" + standard_tools.replace_invalid_tokens(str(partner_id.street[:159])) + """</OtrasSenas>
							</Ubicacion>
							""" + str(correo_electronico) + """
						</Emisor>"""
			else:
				emisor = """
				<Emisor>
					""" + data_company + """
				</Emisor>"""

				receptor = """
				<Receptor>
					<Nombre>""" + standard_tools.replace_invalid_tokens(str(partner_id.name)[:99]) + """</Nombre>
					""" + identificacion + """
					""" + correo_electronico + """
				</Receptor>"""

			# FEE no lleva los nodos exoneracion
			total_serv_exonerado = ''
			total_merc_exonerada = ''
			total_exonerado = ''
			total_iva_devuelto_str = ''
			if type_document != '09':
				total_serv_exonerado = """<TotalServExonerado>""" + str(standard_tools.round_decimal(totalservexonerado, 5)) + """</TotalServExonerado>"""
				total_merc_exonerada = """<TotalMercExonerada>""" + str(standard_tools.round_decimal(totalmercexonerada, 5)) + """</TotalMercExonerada>"""
				total_exonerado = """<TotalExonerado>""" + str(standard_tools.round_decimal(totalservexonerado + totalmercexonerada, 5)) + """</TotalExonerado>"""
				if type_document != '08':
					total_iva_devuelto_str = """<TotalIVADevuelto>""" + str(total_iva_devuelto) + """</TotalIVADevuelto>"""

			otros = ''
			for special_tag in inv.special_tags_lines:
				if special_tag.element == 'CompraEntrega':
					tag = '<' + str(special_tag.code) + '>' + str(special_tag.content) + '</' + str(special_tag.code) + '>\n'
					if otros.find("</CompraEntrega>") >= 0:
						tag += "</CompraEntrega>"
						otros = otros.replace("</CompraEntrega>", tag)
					else:
						otros += """
						<OtroContenido>
							<CompraEntrega xmlns="http://www.gs1cr.org/esquemas/CompraEntrega/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.gs1cr.org/esquemas/CompraEntrega/ http://www.gs1cr.org/esquemas/CompraEntrega/CR_GS1_CompraEntrega_V3_0.xsd">
								""" + tag + """
							</CompraEntrega>
						</OtroContenido>
						"""
				elif special_tag.content:
					tag = '<' + special_tag.element + ' codigo="' + (special_tag.code or '') + '">' + str(special_tag.content) + '</' + special_tag.element + '>\n'
					# Tiene que llevar un orden las etiquetas
					if special_tag.element == 'OtroTexto':
						otros = tag + otros
					else:
						# todo OtroContenido debe llevar dentro solo etiquetas y xmlns, aplicar children
						otros += tag

			otros_cargos_str = ''
			total_otros_cargos_str = ''
			if otros_cargos:
				for code, value in otros_cargos.items():
					porcentaje = ''
					if value['rate'] != 0:
						porcentaje = """<Porcentaje>""" + str(value['rate']) + """</Porcentaje>"""
					otros_cargos_str += """
								<OtrosCargos>
									<TipoDocumento>""" + code + """</TipoDocumento>
									<Detalle>""" + value['name'] + """</Detalle>
									""" + porcentaje + """
									<MontoCargo>""" + str(standard_tools.round_decimal(value['total'], 5)) + """</MontoCargo>
								</OtrosCargos>
								"""
					total_otros_cargos += value['total']

				total_otros_cargos = standard_tools.round_decimal(total_otros_cargos, 5)
				total_otros_cargos_str = """<TotalOtrosCargos>""" + str(total_otros_cargos) + """</TotalOtrosCargos>"""

			if inv.invoice_date_due:
				plazo_credito = (inv.invoice_date_due - inv.invoice_date).days
			else:
				plazo_credito = inv.invoice_payment_term_id.line_ids and inv.invoice_payment_term_id.line_ids[0].days or 0

			if inv.invoice_payment_term_id.sale_conditions_id:
				condicion_venta = inv.invoice_payment_term_id.sale_conditions_id.sequence
			else:
				condicion_venta = plazo_credito == 0 and '01' or '02'

			xml = """<?xml version="1.0" encoding="UTF-8"?>\n"""
			xml += headers[type_document]
			xml += """
			<Clave>""" + inv.number_electronic + """</Clave>
			<CodigoActividad>""" + str(inv.activity_type.code) + """</CodigoActividad>
			<NumeroConsecutivo>""" + inv.name + """</NumeroConsecutivo>
			<FechaEmision>""" + inv.date_issuance + """</FechaEmision>
			""" + emisor + """
			""" + receptor + """
			<CondicionVenta>""" + str(condicion_venta) + """</CondicionVenta>
			<PlazoCredito>""" + str(plazo_credito) + """</PlazoCredito>
			<MedioPago>""" + str(medio_pago) + """</MedioPago> 
			<DetalleServicio>
				""" + detail_lines + """
			</DetalleServicio>
			""" + otros_cargos_str + """
			<ResumenFactura>
				<CodigoTipoMoneda>
      				<CodigoMoneda>""" + str(inv.currency_id.name) + """</CodigoMoneda>
      				<TipoCambio>""" + str(standard_tools.round_decimal(inv.currency_rate_save, 5)) + """</TipoCambio>
    			</CodigoTipoMoneda>
				<TotalServGravados>""" + str(standard_tools.round_decimal(totalserviciogravado, 5)) + """</TotalServGravados>
				<TotalServExentos>""" + str(standard_tools.round_decimal(totalservicioexento, 5)) + """</TotalServExentos>
				""" + total_serv_exonerado + """
				<TotalMercanciasGravadas>""" + str(standard_tools.round_decimal(totalmercaderiagravado, 5)) + """</TotalMercanciasGravadas>
				<TotalMercanciasExentas>""" + str(standard_tools.round_decimal(totalmercaderiaexento, 5)) + """</TotalMercanciasExentas>
				""" + total_merc_exonerada + """
				<TotalGravado>""" + str(standard_tools.round_decimal(totalserviciogravado + totalmercaderiagravado, 5)) + """</TotalGravado>
				<TotalExento>""" + str(standard_tools.round_decimal(totalservicioexento + totalmercaderiaexento, 5)) + """</TotalExento>
				""" + total_exonerado + """
				<TotalVenta>""" + str(standard_tools.round_decimal(totalserviciogravado + totalmercaderiagravado + totalservicioexento + totalmercaderiaexento + totalservexonerado + totalmercexonerada, 5)) + """</TotalVenta>
				""" + total_decuento + """
				<TotalVentaNeta>""" + str(standard_tools.round_decimal(totalserviciogravado + totalmercaderiagravado + totalservicioexento + totalmercaderiaexento + totalservexonerado + totalmercexonerada - resumen_total_discount, 5)) + """</TotalVentaNeta>
				<TotalImpuesto>""" + str(standard_tools.round_decimal(impuestos_total - total_exoneracion, 5)) + """</TotalImpuesto>
				""" + total_iva_devuelto_str + """
				""" + total_otros_cargos_str + """
				<TotalComprobante>""" + str(standard_tools.round_decimal(totalcomprobante - resumen_total_discount + impuestos_total - total_exoneracion - total_iva_devuelto + total_otros_cargos, 5)) + """</TotalComprobante>
			</ResumenFactura>
			""" + informacion_referencia + """
			<Otros>
				<OtroTexto>Generado por www.delfixcr.com con el sistema Odoo</OtroTexto>
				""" + otros + """
				<OtroContenido>
					<ContactoDesarrollador xmlns="http://www.delfixcr.com">Delfix Tecnosoluciones S.A. soporte@delfixcr.com +506 4001-3192 Ext 1001</ContactoDesarrollador>
				</OtroContenido>
			</Otros>
			"""

			# Factura de compra
			if type_document == '08':
				data_to_send = {
					"fecha": inv.date_issuance,
					"clave": inv.number_electronic,
					"receptor": {
						"tipoIdentificacion": str(inv.company_id.identification_id.code),
						"numeroIdentificacion": str(inv.company_id.vat)
					},
				}
				if partner_id.identification_id and partner_id.ref:
					if partner_id.identification_id.code != '05':
						data_to_send.update({
							"emisor": {
								"tipoIdentificacion": str(partner_id.identification_id.code),
								"numeroIdentificacion": str(partner_id.ref)
							}})
			else:
				data_to_send = {
					"fecha": inv.date_issuance,
					"clave": inv.number_electronic,
					"emisor": {
						"tipoIdentificacion": str(inv.company_id.identification_id.code),
						"numeroIdentificacion": str(inv.company_id.vat)
					},
				}
				if partner_id.identification_id and partner_id.ref:
					if partner_id.identification_id.code != '05':
						data_to_send.update({
							"receptor": {
								"tipoIdentificacion": str(partner_id.identification_id.code),
								"numeroIdentificacion": str(partner_id.ref)
							}})

			xml += end_headers[type_document]
			xml_format = minidom.parseString(xml)
			xml = xml_format.toprettyxml()
			xml = os.linesep.join([s for s in xml.splitlines() if s.strip()])

			if config.mode_debug:
				_logger.info('\n---------------------------------\nXML formado:\n' + str(xml) + '\n---------------------------------\n')
			return xml, data_to_send

	def _sign_xml_python(self, cert, password, xml, policy_id='https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.2/ResolucionComprobantesElectronicosDGT-R-48-2016_4.2.pdf'):
		root = etree.fromstring(xml)
		signature = create_xades_epes_signature()

		policy = PolicyId2()
		policy.id = policy_id

		root.append(signature)
		ctx = XAdESContext2(policy)
		certificate = crypto.load_pkcs12(base64.b64decode(cert), password.encode('utf-8'))
		ctx.load_pkcs12(certificate)
		ctx.sign(signature)

		return etree.tostring(root, encoding='UTF-8', method='xml', xml_declaration=True, with_tail=False)

	def _sign_document(self, xml, inv, config):
		if config.mode_debug:
			_logger.info('\n---------------------------------\nFirmando el xml\n---------------------------------\n')

		# Firmado con python
		if config.connection_mode == 'direct_python':
			return self._sign_xml_python(inv.company_id.signature, inv.company_id.frm_pin, xml)

		# Firmado con Java
		# El codigo fuente java esta en el repositorio xades_signer_xml

		# Archivo temporal xml
		temp_xml = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
		temp_xml.write(xml.encode('utf-8'))
		temp_xml.close()
		path_xml = temp_xml.name

		temp_key = tempfile.NamedTemporaryFile(suffix='.p12', delete=False)
		temp_key.write(base64.decodebytes(inv.company_id.signature))
		temp_key.close()
		path_key = temp_key.name

		jar_path = 'signer/xades_java/xades_signer.jar'
		full_path = os.path.join(os.path.dirname(__file__).replace('/models', ''), jar_path)

		xml_sign_path = path_xml + "_sign"

		command = "java -XX:CompressedClassSpaceSize=50m -XX:InitialHeapSize=50m -XX:MaxHeapSize=50m -XX:MaxMetaspaceSize=50m -XX:+UseConcMarkSweepGC -jar " + full_path + " " + path_key + " " + str(inv.company_id.frm_pin) + " " + path_xml + " " + xml_sign_path

		output = subprocess.getoutput(command)
		if output == '':
			xml_sign = open(xml_sign_path, "r").read()
			command = 'rm ' + path_key + ' ' + path_xml + ' ' + xml_sign_path
			os.system(command)
		else:
			inv.electronic_invoice_return_message = output
			xml_sign = False
		if config.mode_debug:
			_logger.info('\n---------------------------------\nResultado de la firma del xml ' + str(output) + '\n---------------------------------\n')
		return xml_sign

	# Envia el payload de la factura a MH
	def _send_xml_mh(self, config, inv, data_to_send):

		if config.mode_debug:
			_logger.info('\n---------------------------------\n' + 'Iniciando envio\n---------------------------------\n')

		if inv.company_id.frm_ws_ambiente == 'stag':
			environment = "recepcion-sandbox"
		else:
			environment = "recepcion"

		token = inv.company_id.get_token_temp()

		headers = {'Content-type': 'application/json;charset=UTF-8', 'Authorization': token}

		requests_url = 'https://api.comprobanteselectronicos.go.cr/' + environment + '/v1/recepcion'

		try:
			response_document = requests.post(requests_url, headers=headers, data=json.dumps(data_to_send))
			if config.mode_debug:
				_logger.info('\n---------------------------------\n' + 'Codigo de respuesta: ' + str(response_document.status_code) + '\n---------------------------------\n')
			if response_document.status_code in (201, 202):
				inv.state_tributacion = 'enviado'
				inv.electronic_invoice_return_message = False
				if config.mode_debug:
					_logger.info('\n---------------------------------\n' + 'XML Enviado a MH: ' + str(inv._name) + ' ' + str(inv.id) + '\n---------------------------------\n')
			elif response_document.status_code == 401:
				# Se deja el estado El token expiro
				pass
			elif response_document.status_code == 400:
				error = response_document.headers.get('X-Error-Cause')
				# Si el documento devuelve el error de que ya fue recibida se cosulta el documento
				if (str(error)).find("ya fue recibido anteriormente") > 0:
					inv.state_tributacion = 'enviado'
					inv.electronic_invoice_return_message = False
					if config.mode_debug:
						_logger.info('\n---------------------------------\n' + 'El documento ya fue recibido anteriormente\n---------------------------------\n')
				else:
					if config.mode_debug:
						_logger.info('\n---------------------------------\nError de FE: \n' + 'Error Respuesta de MH: ' + str(error) + '\n' + ' Error interno de odoo: ' + str(sys.exc_info()) + '\n---------------------------------\n')
					inv.electronic_invoice_return_message = error
					inv.state_tributacion = 'enviado_error'
			elif response_document.status_code == 503:
				# Se deja el estado, el servidor está saturado en ese momento
				pass
			else:
				inv.electronic_invoice_return_message = str(response_document._content)
				inv.state_tributacion = 'enviado_error'
		except:
			if config.mode_debug:
				_logger.info('\n---------------------------------\nError de FE: \n' + str(sys.exc_info()) + '\n---------------------------------\n')
			inv.electronic_invoice_return_message = 'Error interno de odoo: ' + str(sys.exc_info())
			inv.state_tributacion = 'conexion_error'
