# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResCountryStateInherit(models.Model):
	_inherit = ['res.country.state']

	fe_code = fields.Char(string="FE Código", required=False, )


class ResCountryCounty(models.Model):
	_name = "res.country.county"
	_description = 'Cantón'

	code = fields.Char(string="Código", required=False, )
	state_id = fields.Many2one(comodel_name="res.country.state", string="Provincia", required=False, )
	name = fields.Char(string="Nombre", required=False, )


class ResCountryDistrict(models.Model):
	_name = "res.country.district"
	_description = 'Distrito'

	code = fields.Char(string="Código", required=False, )
	county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=False, )
	name = fields.Char(string="Nombre", required=False, )


class ResCountryNeighborhood(models.Model):
	_name = "res.country.neighborhood"
	_description = 'Barrio'

	code = fields.Char(string="Código", required=False, )
	district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=False, )
	name = fields.Char(string="Nombre", required=False, )
