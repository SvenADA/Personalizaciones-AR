# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from collections import defaultdict
from odoo.exceptions import AccessError, ValidationError


class IrAttachmentInherit(models.Model):
	_inherit = "ir.attachment"

	# Se remplaza, el metodo no hace correcta validacion de permisos de attachment
	# cuando estos estan asignados a un res_field
	# Se modifica solo para los res_field: xml_respuesta_tributacion y xml_comprobante
	@api.model
	def check(self, mode, values=None):
		""" Restricts the access to an ir.attachment, according to referred mode """
		if self.env.is_superuser():
			return True
		# Always require an internal user (aka, employee) to access to a attachment
		if not (self.env.is_admin() or self.env.user.has_group('base.group_user')):
			raise AccessError(_("Sorry, you are not allowed to access this document."))
		# collect the records to check (by model)
		model_ids = defaultdict(set)            # {model_name: set(ids)}
		if self:
			# DLE P173: `test_01_portal_attachment`
			self.env['ir.attachment'].flush(['res_model', 'res_id', 'create_uid', 'public', 'res_field'])
			self._cr.execute('SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
			for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
				### Cambio Odoo no deja mostrar a los mail.template los campos binarios para el boton enviar e imprimir
				if not self.env.is_system() and res_field and res_field not in ('xml_respuesta_tributacion', 'xml_comprobante', 'email_attachment'):
					raise AccessError(_("Sorry, you are not allowed to access this document."))
				###Cambio
				if public and mode == 'read':
					continue
				if not (res_model and res_id):
					continue
				model_ids[res_model].add(res_id)
		if values and values.get('res_model') and values.get('res_id'):
			model_ids[values['res_model']].add(values['res_id'])

		# check access rights on the records
		for res_model, res_ids in model_ids.items():
			# ignore attachments that are not attached to a resource anymore
			# when checking access rights (resource was deleted but attachment
			# was not)
			if res_model not in self.env:
				continue
			if res_model == 'res.users' and len(res_ids) == 1 and self.env.uid == list(res_ids)[0]:
				# by default a user cannot write on itself, despite the list of writeable fields
				# e.g. in the case of a user inserting an image into his image signature
				# we need to bypass this check which would needlessly throw us away
				continue
			records = self.env[res_model].browse(res_ids).exists()
			# For related models, check if we can write to the model, as unlinking
			# and creating attachments can be seen as an update to the model
			access_mode = 'write' if mode in ('create', 'unlink') else mode
			records.check_access_rights(access_mode)
			records.check_access_rule(access_mode)

	#Evitar eliminar xml por medio de los correos enviados en el chatter
	def unlink(self):
		for attachment in self:
			if attachment.res_field in ('xml_respuesta_tributacion', 'xml_comprobante', 'xml_supplier_approval'):
				res_model = self.env[attachment.res_model].search([('id', '=', attachment.res_id)], limit=1)
				if res_model and res_model.state_tributacion:
					raise ValidationError("No esta permitido eliminar XMLs validados")
		return super(IrAttachmentInherit, self).unlink()


