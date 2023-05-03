# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductCategoryElectronic(models.Model):
	_inherit = "product.category"

	cabys_code = fields.Char(string="Código Cabys", required=False, help='Código obtenido del Catálogo de bienes y servicios (Cabys), el codigo tambien puede ser definido a nivel de Categoría Padre (Dejando vacío el campo. Nota: El código de la Categoría Hija tiene prioridad sobre el código de la Categoría Padre)')
	cabys_description = fields.Text(string="Descripción Cabys", required=False, )

	def get_cabys_code(self):
		if self.cabys_code:
			return self.cabys_code
		else:
			if self.parent_id:
				return self.parent_id.get_cabys_code()
		return False

	@api.constrains('cabys_code')
	def _check_cabys_code(self):
		for record in self:
			if record.cabys_code:
				if len(record.cabys_code) != 13:
					raise ValidationError('Error de Facturación Electrónica\n El Código Cabys debe de tener un tamaño de 13 dígitos')

	def action_search_cabys(self):
		return self.env['product.result.cabys.wizard'].action_search_cabys(self)
