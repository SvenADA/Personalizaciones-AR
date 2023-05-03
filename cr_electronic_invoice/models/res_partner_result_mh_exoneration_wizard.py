# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartnerResultMhExonerationWizard(models.TransientModel):
	_name = 'res.partner.result.mh.exoneration.wizard'
	_description = 'Resultado de consulta en MH'

	res_partner_id = fields.Many2one(comodel_name="res.partner", string="Contacto", required=False, )
	name = fields.Char(string="Numero Documento", required=False, copy=False)
	ref = fields.Char(string="Cédula", required=False, copy=False)
	date_issue = fields.Date(string="Fecha de emisión", required=False, )
	due_date = fields.Date(string="Fecha de vencimiento", required=False, )
	document_type = fields.Char(string="Tipo de documento", required=False, copy=False)
	name_institution = fields.Char(string="Nombre de institución", required=False, copy=False)
	exoneration_percentage = fields.Integer(string="Porcentaje", required=False, )
	cabys_line_ids = fields.One2many('exoneration.cabys.line.wizard', 'exoneration_id', string='Cabys permitidos')
	code_cfia = fields.Char(string="Código Proyecto CFIA", required=False, copy=False)

	def consult_exoneration_wizard(self):
		exoneration = self.env['exoneration.tax.electronic.invoice']
		response = exoneration._consult_exo_code(self.name)
		return exoneration.exoneration_wizard(response)

	def create_exoneration_wizard(self):
		exoneration_type = self.env['exoneration.type'].search([('code', '=', '04')], limit=1)
		cabys_line_ids = [(0, 0, {'code': cabys.code}) for cabys in self.cabys_line_ids]
		exoneration = self.env['exoneration.tax.electronic.invoice'].create({
			'partner_id': self.res_partner_id.id,
			'name': self.name,
			'document_type_id': exoneration_type.id,
			'institution_name': self.name_institution,
			'document_number': self.name,
			'date_issue': self.date_issue,
			'due_date': self.due_date,
			'purchase_percentage': self.exoneration_percentage,
			'validate_cabys': bool(cabys_line_ids),
			'cabys_line_ids': cabys_line_ids,
		})
		position_tax_id = self._context.get('account_position_tax_id', 0)
		account_position_tax_id = self.env['account.fiscal.position.tax'].search([('id', '=', position_tax_id)], limit=1)
		if exoneration_type:
			account_position_tax_id.exoneration = exoneration


class ExonerationCabysLineWizard(models.TransientModel):
	_name = "exoneration.cabys.line.wizard"
	_description = "Lineas de cabys de exoneracion wizard"

	exoneration_id = fields.Many2one('res.partner.result.mh.exoneration.wizard', string='Documento de Exoneración', ondelete='cascade', index=True)
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
