# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartnerResultMhWizard(models.TransientModel):
	_name = 'res.partner.result.mh.wizard'
	_description = 'Resultado de consulta de cliente en MH'

	res_partner_id = fields.Many2one(comodel_name="res.partner", string="Contacto", required=False, )
	name = fields.Char(string="Nombre", required=False, copy=False)
	identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificacion", required=False, )
	ref = fields.Char(string="Cédula", required=False, copy=False)

	regime = fields.Char(string="Régimen", required=False, copy=False)

	defaulter = fields.Char(string="Moroso", required=False, copy=False)
	omitted = fields.Char(string="Omiso", required=False, copy=False)
	state = fields.Char(string="Estado", required=False, copy=False)
	tax_administration = fields.Char(string="Administración Tributaria", required=False, copy=False)

	activity_lines = fields.One2many(comodel_name="res.partner.result.mh.activity.lines.wizard", inverse_name="res_partner_result_mh_id", string="Líneas de actividades económicas", required=False, )
	mag_lines = fields.One2many(comodel_name="res.partner.result.mh.mag.lines.wizard", inverse_name="res_partner_result_mh_id", string="Líneas de MAG", required=False, )
	name_lowercase = fields.Boolean(string='Nombre a minúscula', required=False, help="Se transforma el nombre a minúscula con formato de título, algunos términos pueden ser incorrectos")
	email = fields.Char(string='Correo', required=False)
	is_additional_mail = fields.Boolean(string='Guardar como correo adicional', required=False)

	@api.onchange('name_lowercase')
	def onchange_name_lowercase(self):
		if self.name:
			if self.name_lowercase:
				self.name = self.name.title()
			else:
				self.name = self.name.upper()

	def save_all(self):
		self.save_name()
		self.save_email()
		self.save_activities()

	def save_name(self):
		self.res_partner_id.name = self.name

	def save_email(self):
		if self.email:
			emails = [e for e in self.email.split(',')]

			if not self.is_additional_mail:
				self.res_partner_id.email = emails.pop(0)

			for email in emails:
				if not self.res_partner_id.emails_ids.filtered(lambda l: l.name == email):
					self.env['mails.electronic.invoice'].create({
						'res_partner_id': self.res_partner_id.id,
						'name': email,
					})

	def save_activities(self):
		new_activities = list()
		for activity in self.activity_lines:
			activity_codes = self.env['activity.code'].search([('code', '=', activity.code)], limit=1)
			if not activity_codes:
				new_activity = activity_codes.sudo().create({
					'code': activity.code,
					'name': activity.name,
				})
				new_activities.append(new_activity.id)
			else:
				new_activities.append(activity_codes.id)

		if new_activities:
			if self.res_partner_id.activity_types:
				new_activities.extend(self.res_partner_id.activity_types.ids)
			self.res_partner_id.write({'activity_types': [[6, False, new_activities]]})


class ResPartnerResultMhActivityLinesWizard(models.TransientModel):
	_name = 'res.partner.result.mh.activity.lines.wizard'
	_description = 'Resultado de consulta de cliente en MH Actividades Economicas'

	res_partner_result_mh_id = fields.Many2one(comodel_name="res.partner.result.mh.wizard", string="Resultado de consulta", required=False, ondelete='cascade', index=True)
	name = fields.Char(string="Nombre", required=False, copy=False)
	code = fields.Char(string="Codigo", required=False, copy=False)


class ResPartnerResultMhMagLinesWizard(models.TransientModel):
	_name = 'res.partner.result.mh.mag.lines.wizard'
	_description = 'Resultado de consulta de cliente en MH MAG'

	res_partner_result_mh_id = fields.Many2one(comodel_name="res.partner.result.mh.wizard", string="Resultado de consulta", required=False, ondelete='cascade', index=True)
	type = fields.Selection(string="Tipo", selection=[
		('mag', 'MAG'),
		('incopesca', 'INCOPESCA'),
		('acuicultores', 'Acuicultores'),
	], required=False, )
	due_date = fields.Date(string="Fecha de vencimiento", required=False, )
	validity = fields.Boolean(string="Activo", )
