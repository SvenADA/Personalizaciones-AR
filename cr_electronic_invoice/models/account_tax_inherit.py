# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InvoiceTaxElectronic(models.Model):
	_inherit = "account.tax"

	tax_type = fields.Many2one(comodel_name="invoice.tax.type", string="Tipo de impuesto", )
	tax_rate = fields.Many2one(comodel_name="invoice.tax.code.rate", string="Tarifa", help="La tarifa es requerida cuando el tipo de impuesto es: Impuesto al valor agregado o IVA (cálculo especial)")
	other_charge = fields.Many2one(comodel_name="type.other.charges", string="Otro cargo", help="Cargos directos al cliente")

	@api.constrains('tax_type')
	def _check_tax_rate(self):
		for record in self:
			if record.tax_type and record.tax_type.code in ('01', '07'):
				if not record.tax_rate:
					raise ValidationError('Error de Facturación Electrónica\n La tarifa es requerida cuando el tipo de impuesto es: Impuesto al valor agregado o IVA (cálculo especial)')

	@api.onchange('tax_rate')
	def _onchange_tax_rate(self):
		if self.tax_rate:
			self.amount = self.tax_rate.rate

	@api.onchange('other_charge')
	def _onchange_other_charge(self):
		if self.other_charge:
			self.name = self.other_charge.name
			self.tax_type = self.env['invoice.tax.type'].search([('code', '=', '00')], limit=1)
			if self.other_charge.code == '06':
				self.amount = 10
			else:
				self.amount = 0
