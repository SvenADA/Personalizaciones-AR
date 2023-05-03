# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

uom_service = ('Sp', 'Os', 'Spe', 'St', 'Alc', 'Al', 's', 'min', 'h', 'd', 'Cm', 'I')


class ProductTemplateElectronic(models.Model):
	_inherit = "product.template"

	@api.model
	def _default_code_type_id(self):
		code_type_id = self.env['code.type.product'].search([('code', '=', '04')], limit=1)
		return code_type_id or False

	commercial_measurement = fields.Char(string="Unidad de Medida Comercial", required=False, )
	code_type_id = fields.Many2one(comodel_name="code.type.product", string="Tipo de código", required=False, default=_default_code_type_id, help="Indica el tipo de código utilizado para identificar los productos. Se relaciona con el campo 'Referencia interna'")
	tariff_item = fields.Char(string="Partida Arancelaria", required=False, size=12)
	return_iva = fields.Boolean(string="Devolver IVA", help="Si el pago es por tarjeta y este campo está marcado se enviará a MH el Impuesto devuelto al consumidor. (Solo aplica para servicios de salud)")
	cabys_code = fields.Char(string="Código Cabys", required=False, help='Código obtenido del Catálogo de bienes y servicios (Cabys), el codigo tambien puede ser definido a nivel de Categoría (Dejando el campo vacío. Nota: El código del producto tiene prioridad sobre el código de la Categoría)')
	cabys_description = fields.Text(string="Descripción Cabys", required=False, )

	@api.constrains('cabys_code')
	def _check_cabys_code(self):
		for record in self:
			if record.cabys_code:
				if len(record.cabys_code) != 13:
					raise ValidationError('Error de Facturación Electrónica\n El Código Cabys debe de tener un tamaño de 13 dígitos')

	@api.constrains('cabys_code', 'categ_id', 'sale_ok')
	def _check_required_cabys(self):
		for rec in self:
			if rec.sale_ok and not rec.get_cabys_code():
				raise ValidationError("Por favor ingrese un código cabys en el producto o categoría")

	@api.constrains('tariff_item')
	def _check_tariff_item(self):
		for record in self:
			if record.tariff_item:
				if len(record.tariff_item) != 12:
					raise ValidationError('Error de Facturación Electrónica\n La Partida Arancelaria debe de tener un tamaño de 12 dígitos')

	@api.constrains('property_account_income_id', 'categ_id', 'sale_ok')
	def _check_property_account_income_id(self):
		for rec in self:
			if rec.sale_ok and not rec.property_account_income_id and not rec.categ_id.property_account_income_categ_id:
				raise ValidationError("Por favor ingrese una cuenta en el campo 'Cuenta de ingresos' en el producto o categoría")

	@api.constrains('type', 'uom_id', 'sale_ok')
	def _check_type_uom_id(self):
		for record in self:
			# Se validan las unidades de medida de Servicios
			if record.sale_ok and record.type and record.uom_id:
				if record.type == 'service':
					if record.uom_id.code not in uom_service:
						raise ValidationError('El producto es un servicio y su unidad de medida es: ' + str(record.uom_id.name) + ', por favor proceder a modificar la unidad de medida de acuerdo al servicio.')
				else:
					if record.uom_id.code in uom_service:
						raise ValidationError('El producto es una mercancía y su unidad de medida es: ' + str(record.uom_id.name) + ', por favor proceder a modificar la unidad de medida de acuerdo a la mercancía.')

	def get_cabys_code(self):
		if self.cabys_code:
			return self.cabys_code
		else:
			if self.categ_id:
				return self.categ_id.get_cabys_code()
		return False

	def action_search_cabys(self):
		return self.env['product.result.cabys.wizard'].action_search_cabys(self)

	@api.onchange('type')
	def _onchange_type(self):
		res = super(ProductTemplateElectronic, self)._onchange_type()
		if self.type:
			if self.type == 'service':
				uom_id = self.env.ref('cr_electronic_invoice.ei_product_uom_Os')
			else:
				uom_id = self.env.ref('uom.product_uom_unit')
			self.uom_id = uom_id
			self.uom_po_id = uom_id
		return res

	@api.model
	def create(self, values):
		if values.get('type', False) == 'service':
			uom_id = self.env['uom.uom'].browse(values.get('uom_id'))
			if uom_id.code not in uom_service:
				uom_os_id = self.env.ref('cr_electronic_invoice.ei_product_uom_Os').id
				values.update({
					'uom_id': uom_os_id,
					'uom_po_id': uom_os_id,
				})
		return super(ProductTemplateElectronic, self).create(values)


class ProductElectronic(models.Model):
	_inherit = "product.product"

	def get_cabys_code(self):
		if self.cabys_code:
			return self.cabys_code
		else:
			if self.categ_id:
				return self.categ_id.get_cabys_code()
		return False

	def action_search_cabys(self):
		return self.env['product.result.cabys.wizard'].action_search_cabys(self)

	@api.onchange('type')
	def _onchange_type(self):
		if self.type:
			if self.type == 'service':
				uom_id = self.env.ref('cr_electronic_invoice.ei_product_uom_Os')
			else:
				uom_id = self.env.ref('uom.product_uom_unit')
			self.uom_id = uom_id
			self.uom_po_id = uom_id
