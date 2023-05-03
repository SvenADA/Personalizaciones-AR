# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from . import standard_tools


class AccountJournalInherit(models.Model):
	_inherit = ['account.journal']

	electronic_invoice = fields.Boolean(string="Diario para FE", required=False, help='Habilita el requerido de las secuencias y otras validaciones para Facturación Electrónica')

	sucursal = fields.Char(string="Sucursal", required=True, default="001", help="Ejemplo: sucursal de Puntarenas 001, sucursal de Guanacaste 002, etc.")
	terminal = fields.Char(string="Terminal", required=True, default="00001", help="Ejemplo: Puntarenas tiene tres puntos de venta, cada una representa una terminal las que serían 00001, 00002, etc. Pertenecientes a la sucursal 001, Resultado: 00100001, 00100002, etc.")

	# Secuencias Mensaje Receptor
	sequence_electronic_invoice_provider = fields.Many2one(comodel_name="ir.sequence", string="Mensaje Receptor (Aceptación)", required=False)
	partial_acceptance_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Mensaje Receptor (Aceptación Parcial)", required=False)
	rejection_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Mensaje Receptor (Rechazo)", required=False)

	# Secuencias Tiquete, Compra, Exportacion, Nota de debito
	export_invoice_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Factura de exportación", required=False)
	ticket_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Tiquete", required=False)
	purchase_invoice_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Factura de compra", required=False)
	debit_note_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Nota de débito", required=False)
	electronic_invoice_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Factura", required=False)
	credit_note_sequence_id = fields.Many2one(comodel_name="ir.sequence", string="Nota de Crédito", required=False)

	@api.constrains('sucursal', 'terminal')
	def _check_sucursal_terminal(self):
		for rec in self:
			if rec.sucursal and rec.terminal:
				standard_tools.validate_sucursal(rec.sucursal)
				standard_tools.validate_terminal(rec.terminal)
