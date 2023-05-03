# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FeSpecialTagsCompanyLine(models.Model):
	_name = "fe.special.tags.company.line"
	_description = 'Líneas para el nodo otros del xml Conpany'

	company_id = fields.Many2one(comodel_name="res.company", string="Conpania", required=False, ondelete='cascade', index=True)
	element = fields.Selection(string="Elemento", selection=[
		('OtroTexto', 'OtroTexto'),
		('OtroContenido', 'OtroContenido'),
		('CompraEntrega', 'CompraEntrega'),
	], required=False, default='OtroTexto')
	code = fields.Char(string="Código Técnico", required=False, )
	content_label = fields.Char(string="Ayuda", required=False, )
	content = fields.Char(string="Contenido", required=False, )
	required = fields.Boolean(string="Requerido (Contenido)", )
	read_only = fields.Boolean(string="Solo lectura (Elemento y Código Técnico)", )
	read_only_content = fields.Boolean(string="Solo lectura (Contenido)", )
	python_code = fields.Text(string="Codigo Python", )
	add_in = fields.Selection(string='Añadir en', selection=[
		('out_invoice', 'Factura'),
		('out_refund', 'Nota de crédito'),
	], required=False, )


class FeSpecialTagsInvoiceLine(models.Model):
	_name = "fe.special.tags.invoice.line"
	_description = 'Líneas para el nodo otros del xml Facturas'

	invoice_id = fields.Many2one(comodel_name="account.move", string="Factura", required=False, ondelete='cascade', index=True)
	element = fields.Selection(string="Elemento", selection=[
		('OtroTexto', 'OtroTexto'),
		('OtroContenido', 'OtroContenido'),
		('CompraEntrega', 'CompraEntrega'),
	], required=False, default='OtroTexto')
	code = fields.Char(string="Código Técnico", required=False, )
	content_label = fields.Char(string="Ayuda", required=False, )
	content = fields.Char(string="Contenido", required=False, )
	required = fields.Boolean(string="Requerido", )
	read_only = fields.Boolean(string="Solo lectura", )
	read_only_content = fields.Boolean(string="Solo lectura (Contenido)", )
	python_code = fields.Text(string="Codigo Python", )
	type_add = fields.Char(string="Tipo de agregado de linea", required=False, )
	rel_id = fields.Integer(string="Id de special tags", required=False, )


class FeSpecialTagsPartnerLine(models.Model):
	_name = "fe.special.tags.partner.line"
	_description = 'Líneas para el nodo otros del xml Partner'

	partner_id = fields.Many2one(comodel_name="res.partner", string="Contacto", required=False, ondelete='cascade', index=True)
	element = fields.Selection(string="Elemento", selection=[
		('OtroTexto', 'OtroTexto'),
		('OtroContenido', 'OtroContenido'),
		('CompraEntrega', 'CompraEntrega'),
	], required=False, default='OtroTexto')
	code = fields.Char(string="Código Técnico", required=False, )
	content_label = fields.Char(string="Ayuda", required=False, )
	content = fields.Char(string="Contenido", required=False, )
	required = fields.Boolean(string="Requerido (Contenido)", )
	read_only = fields.Boolean(string="Solo lectura (Elemento y Código Técnico)", )
	read_only_content = fields.Boolean(string="Solo lectura (Contenido)", )
	python_code = fields.Text(string="Codigo Python", )
	add_in = fields.Selection(string='Añadir en', selection=[
		('out_invoice', 'Factura'),
		('out_refund', 'Nota de crédito'),
	], required=False, )

