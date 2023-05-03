# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ConfigElectronicInvoiceMH(models.Model):
	_inherit = 'config.electronic.invoice'

	connection_mode = fields.Selection(string="Modo de conexión", selection=[
		('direct', 'Directo Java'),
		('direct_python', 'Directo Python'),
		('cyberfuel', 'Cyberfuel'),
	], required=False, default='cyberfuel', help="""
	*Cyberfuel: Se le envía los datos de la factura a Cyberfuel y retorna el xml firmado, además envía la FE.
	*Directo: Se realiza todo el proceso en el servidor: Creación del xml, firmado y envío a MH."""
	)
