# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import urllib.parse


class ProductResultCabysWizard(models.TransientModel):
	_name = 'product.result.cabys.wizard'
	_description = 'Resultado de consulta de cabys en MH'

	product_name = fields.Char(string="Nombre de producto", required=False, copy=False)
	model_name = fields.Char(string="Modelo", required=False, copy=False)
	model_active_id = fields.Integer(string='ID activo', required=False, copy=False)
	code = fields.Char(string="Código Cabys", required=False, copy=False)
	type_search = fields.Selection([
		('by_name', 'Por nombre'),
		('by_code', 'Por código')
	], string='Tipo de búsqueda', readonly=False, required=True, copy=False, default='by_name')
	line_ids = fields.One2many(comodel_name="product.result.cabys.line.wizard", inverse_name="product_result_cabys_id", string="Líneas de cabys", required=False, )

	def action_search_cabys(self, rec):
		action = self.sudo().env.ref('cr_electronic_invoice.action_product_result_cabys_wizard').read()[0]
		result_wizard = self.env['product.result.cabys.wizard'].create({
			'product_name': rec.name,
			'code': rec.cabys_code,
			'type_search': (rec.cabys_code and 'by_code') or 'by_name',
			'model_name': rec._name,
			'model_active_id': rec.id,
		})
		action.update({
			'res_id': result_wizard.id
		})
		return action

	def save_search_cabys(self):

		rec = self.env[self.model_name].browse(self.model_active_id)

		cabys = [cabys for cabys in self.line_ids if cabys.apply_cabys]
		cabys_len = len(cabys)
		if cabys_len > 1:
			raise UserError('Por favor seleccione un único código')
		elif cabys_len < 1:
			raise UserError('Por favor seleccione un código')

		rec.cabys_code = cabys[0].code
		rec.cabys_description = cabys[0].description

	def search_cabys(self):
		if self.type_search == 'by_name':
			url_product_name = urllib.parse.quote(str(self.product_name))
			url = 'https://api.hacienda.go.cr/fe/cabys?q=' + url_product_name
			response = self._consult_cabys(url)
			response_cabys = response.get('cabys', [])
		else:
			if len(self.code) != 13:
				raise UserError('El Código Cabys debe de tener un tamaño de 13 dígitos')
			url = 'https://api.hacienda.go.cr/fe/cabys?codigo=' + str(self.code)
			response = self._consult_cabys(url)
			response_cabys = response

		self.line_ids.unlink()

		cabys = list()
		for line in response_cabys:
			cabys.append((0, 0, {
				'code': line.get('codigo'),
				'description': line.get('descripcion'),
				'categories_ids': [(0, 0, {'description': cat}) for cat in line.get('categorias')],
				'tax': line.get('impuesto'),
			}))

		self.write({'line_ids': cabys})
		action = self.sudo().env.ref('cr_electronic_invoice.action_product_result_cabys_wizard').read()[0]
		action.update({
			'res_id': self.id
		})
		return action

	def _consult_cabys(self, url=None):
		try:
			response_document = requests.get(url)
			response_content = json.loads(str(response_document._content, 'utf-8'))
		except:
			raise UserError('No fue posible obtener respuesta del servicio del Ministerio de Hacienda, por favor vuelva a intentarlo, si el problema persiste contacte con soporte.')

		if response_document.status_code == 200:
			return response_content
		elif response_document.status_code == 404:
			raise UserError('Código Cabys no encontrado en la base de datos de MH')
		else:
			raise UserError('Error desconocido')


class ProductResultCabysLineWizard(models.TransientModel):
	_name = 'product.result.cabys.line.wizard'
	_description = 'Resultado de consulta de cabys en MH linea'

	product_result_cabys_id = fields.Many2one(comodel_name="product.result.cabys.wizard", string="Resultado de consulta cabys", required=False, ondelete='cascade', index=True)
	code = fields.Char(string="Código", required=False, copy=False)
	description = fields.Text(string="Descripción", required=False, )
	categories_ids = fields.One2many(comodel_name="product.result.cabys.category.line.wizard", inverse_name="product_result_cabys_line_id", string="Categorías", required=False, )
	tax = fields.Integer(string='Impuesto', required=False, copy=False)
	apply_cabys = fields.Boolean(string='Aplicar', required=False, copy=False)


class ProductResultCabysCategoryLineWizard(models.TransientModel):
	_name = 'product.result.cabys.category.line.wizard'
	_description = 'Descripción de categoría'

	product_result_cabys_line_id = fields.Many2one(comodel_name="product.result.cabys.line.wizard", string="Linea cabys", required=False, ondelete='cascade', index=True)
	description = fields.Text(string="Descripción de categorías", required=False, )
