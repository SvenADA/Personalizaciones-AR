# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseInvoiceWizard(models.TransientModel):
	_name = 'purchase.invoice.wizard'
	_description = 'Wizard para creación de factura de proveedor'

	electronic_voucher_supplier_id = fields.Many2one(comodel_name="electronic.voucher.supplier", string="CE", required=False)
	line_ids = fields.One2many(comodel_name='purchase.invoice.line.wizard', inverse_name='purchase_invoice_wizard_id', string='Lineas', copy=False)

	def create_invoice(self):
		for line in self.line_ids:
			if not line.account_id:
				raise ValidationError('Por favor agregue una cuenta para la descripción: %s...' % line.detail[:100])

		result = self.electronic_voucher_supplier_id.create_invoice(wizard=self)
		return result


class PurchaseInvoiceLineWizard(models.TransientModel):
	_name = 'purchase.invoice.line.wizard'
	_description = 'Wizard para creación de factura de proveedor lineas'

	purchase_invoice_wizard_id = fields.Many2one(comodel_name='purchase.invoice.wizard', string='Wizard para creación de factura de proveedor', ondelete='cascade', copy=False)
	company_id = fields.Many2one(comodel_name="res.company", string="Compania", required=False, )
	detail = fields.Char(string="Descripción", required=False, )
	product_id = fields.Many2one(comodel_name='product.product', string='Producto', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Producto que corresponda con la descripción")
	account_id = fields.Many2one(comodel_name='account.account', string='Cuenta', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Cuenta que corresponda con la descripción")
	electronic_voucher_line_id = fields.Many2one(comodel_name='electronic.voucher.supplier.line', string='CE Linea')

	@api.onchange('product_id')
	def onchange_product(self):
		for line in self:
			if line.product_id:
				line.account_id = line.product_id.property_account_expense_id
