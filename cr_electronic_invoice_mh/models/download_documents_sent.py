# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import requests
from odoo.exceptions import UserError


class ElectronicVoucherSupplier(models.TransientModel):
	_name = "download.documents.sent"
	_description = 'Consulta de documentos enviados a MH'

	partner_id = fields.Many2one(comodel_name="res.partner", string="Cliente")
	invoice_id = fields.Many2one(comodel_name="account.move", string="Factura")
	limit = fields.Integer(string="Cantidad de facturas", required=False, help="Cantidad de items a retornar apartir del numero de factura ingresado", default=2)
	offset = fields.Integer(string="A partir de la factura#", required=False, help="A partir de qué posición contar los ítems a retornar, Ej: Si ‘Cantidad de facturas’ = 100, y’ A partir de la factura#’ = 50, se obtendrán las facturas número 101,103,104,...,150 recibidas por MH, Nota: Los datos ingresados no tiene relación con el consecutivo de las facturas, son facturas que MH enumera desde la primera hasta la última recibida, por orden de acuse.")
	lines_ids = fields.One2many(comodel_name="download.documents.sent.lines", inverse_name="download_documents_sent_id", string='Comprobantes Electronicos', )
	consult_invoce = fields.Boolean(string="Consultar Factura", )
	number_electronic = fields.Char(string="Número electrónico", required=False, copy=False)

	def download_document_sent(self):
		if self.limit > 50:
			raise UserError('Error de Facturación Electrónica\n\n El máximo de FE a consultar es de 50')

		# Se obtiene el numero electronico
		company_id = self.env.user.company_id

		if company_id.frm_ws_ambiente == 'stag':
			environment = "recepcion-sandbox"
		else:
			environment = "recepcion"

		token = company_id.get_token_temp()

		headers = {'Content-type': 'application/json;charset=UTF-8', 'Authorization': token}

		if self.consult_invoce or self.number_electronic:
			receptor = ''
			emisor = ''
			limit = ''
			offset = ''
			number_elec = self.invoice_id.number_electronic or self.number_electronic
		else:
			receptor = ''
			if self.partner_id:
				receptor = "&receptor=" + str(self.partner_id.identification_id.code) + str(self.partner_id.ref)
			emisor = "?emisor=" + str(company_id.identification_id.code) + str(company_id.vat)
			limit = "&limit=" + str(self.limit)
			offset = "&offset=" + str(self.offset)
			number_elec = ''

		requests_url = 'https://api.comprobanteselectronicos.go.cr/' + environment + '/v1/comprobantes/' + number_elec + emisor + receptor + limit + offset

		try:
			response_document = requests.get(requests_url, headers=headers)
			response_content = response_document.json()
			if response_document.status_code in (206, 200):
				self.lines_ids.unlink()
				if self.consult_invoce:
					self.create_line(response_content)
					for nc in response_content.get('notasCredito'):
						self.create_line(nc)
					for nd in response_content.get('notasDebito'):
						self.create_line(nd)
				else:
					for line_select in response_content:
						self.create_line(line_select)
						for nc in line_select.get('notasCredito'):
							self.create_line(nc)
						for nd in line_select.get('notasDebito'):
							self.create_line(nd)
			elif response_document.status_code == 401:
				pass
			else:
				raise UserError('Error de Facturación Electrónica\n No fue posible obtener las Facturas Electronicas del MH, por favor vuelva a intentarlo')
		except:
			raise UserError('Error de Facturación Electrónica\n No fue posible obtener las Facturas Electronicas del MH, por favor vuelva a intentarlo')

	def create_line(self, dic_line):
		number_electronic = dic_line.get('clave')
		type_str = ''
		cliente = False
		if number_electronic[29:31] == '03':
			type_str = '-----> NC '
		elif number_electronic[29:31] == '02':
			type_str = '-----> ND '
		else:
			cliente = dic_line.get('receptor').get('nombre')

		invoice = self.env['account.move'].search([
			('number_electronic', '=', number_electronic),
		], limit=1, )

		date = datetime.strptime(dic_line.get('fecha'), "%Y-%m-%dT%H:%M:%S-06:00")

		dic_line = {
			'number_electronic': type_str + number_electronic,
			'invoice_id': invoice.id,
			'download_documents_sent_id': self.id,
			'date': date,
			'partner': cliente
		}
		self.lines_ids.create(dic_line)


class DownloadDocumentsSentLines(models.TransientModel):
	_name = "download.documents.sent.lines"
	_description = 'Consulta de documentos enviados a MH lineas'

	download_documents_sent_id = fields.Many2one(comodel_name="download.documents.sent", ondelete='cascade', index=True, )
	number_electronic = fields.Char(string="Número electrónico", required=False, copy=False)
	invoice_id = fields.Many2one(comodel_name="account.move", string="Factura")
	partner = fields.Char(string="Cliente", required=False, copy=False)
	date = fields.Date(string="Fecha", required=False, )

	rec_name = "number_electronic"
