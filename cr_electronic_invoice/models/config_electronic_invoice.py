# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ConfigElectronicInvoice(models.Model):
	_name = 'config.electronic.invoice'
	_description = 'Configuración de Facturación Electrónica General'

	name = fields.Char(default="Configuración de Facturación Electrónica")
	max_send_invoice = fields.Integer(
		string="Maximo de envios a MH", required=True,
		help='Si ingresa 0 se tomaran todas las facturas')
	max_invoice_consult = fields.Integer(
		string="Maximo de consultas a MH", required=True,
		help='Si ingresa 0 se tomaran todas las facturas'
	)
	mode_debug = fields.Boolean(
		string="DEBUG",
		help="Imprime en la terminal del servidor el proceso de facturación electrónica, \n" +
		     "*Las facturas que se cargan\n" +
		     "*La factura que está en proceso\n" +
		     "*Los datos que se envían a MH\n" +
		     "*El número electrónico de la factura enviada\n" +
		     "*Errores relacionados\n" +
		     "\n" +
		     "*Mantener desactivado, si no es necesario el depurador"
	)
	max_send_supplier = fields.Integer(
		string="Maximo de envios a MH (CE)", required=True,
		help='Si ingresa 0 se tomaran todas las facturas')

	# Se extrae las configuraciones del pos
	def get_config(self):
		config = self.env['config.electronic.invoice'].search([('id', '=', 1)], limit=1)
		return config

	# Necesario para que se ejecute el create y guarde los cambios
	def save_config(self):
		pass

	@api.model
	def create(self, values):
		config = self.get_config()
		if config:
			config.update(values)
			return config
		else:
			return super(ConfigElectronicInvoice, self).create(values)
