# -*- coding: utf-8 -*-

import base64
import email
import email.policy
import logging
import sys
from email.message import EmailMessage
from xmlrpc import client as xmlrpclib

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailThreadInherit(models.AbstractModel):
	_inherit = "mail.thread"

	@api.model
	def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
		""" Attempt to figure out the correct target model, thread_id,
		custom_values and user_id to use for an incoming message.
		Multiple values may be returned, if a message had multiple
		recipients matching existing mail.aliases, for example.

		The following heuristics are used, in this order:

		 * if the message replies to an existing thread by having a Message-Id
		   that matches an existing mail_message.message_id, we take the original
		   message model/thread_id pair and ignore custom_value as no creation will
		   take place;
		 * look for a mail.alias entry matching the message recipients and use the
		   corresponding model, thread_id, custom_values and user_id. This could
		   lead to a thread update or creation depending on the alias;
		 * fallback on provided ``model``, ``thread_id`` and ``custom_values``;
		 * raise an exception as no route has been found

		:param string message: an email.message instance
		:param dict message_dict: dictionary holding parsed message variables
		:param string model: the fallback model to use if the message does not match
			any of the currently configured mail aliases (may be None if a matching
			alias is supposed to be present)
		:type dict custom_values: optional dictionary of default field values
			to pass to ``message_new`` if a new record needs to be created.
			Ignored if the thread record already exists, and also if a matching
			mail.alias was found (aliases define their own defaults)
		:param int thread_id: optional ID of the record/thread from ``model`` to
			which this mail should be attached. Only used if the message does not
			reply to an existing thread and does not match any mail alias.
		:return: list of routes [(model, thread_id, custom_values, user_id, alias)]

		:raises: ValueError, TypeError
		"""
		# Solo aplica para el modelo electronic.voucher.supplier
		if model != 'electronic.voucher.supplier':
			return super(MailThreadInherit, self).message_route(message, message_dict, model, thread_id, custom_values)

		if not isinstance(message, EmailMessage):
			raise TypeError('message must be an email.message.EmailMessage at this point')

		fallback_model = model

		# get email.message.Message variables for future processing
		message_id = message_dict['message_id']

		# author and recipients
		email_from = message_dict['email_from']
		email_to = message_dict['to']

		# Cambio
		# Se pasa el Fallback de primero para que no se hagan redirecciones a otros modelos
		# 3. Fallback to the provided parameters, if they work
		if fallback_model:
			# no route found for a matching reference (or reply), so parent is invalid
			message_dict.pop('parent_id', None)
			user_id = self._mail_find_user_for_gateway(email_from).id or self._uid
			route = self._routing_check_route(
				message, message_dict,
				(fallback_model, thread_id, custom_values, user_id, None),
				raise_exception=True)
			if route:
				_logger.info(
					'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
					email_from, email_to, message_id, fallback_model, thread_id, custom_values, user_id)
				return [route]

		# ValueError if no routes found and if no bounce occured
		raise ValueError(
			'No possible route found for incoming message from %s to %s (Message-Id %s:). '
			'Create an appropriate mail.alias or force the destination model.' %
			(email_from, email_to, message_id)
		)

	@api.model
	def message_process(self, model, message, custom_values=None,
			save_original=False, strip_attachments=False,
			thread_id=None):
		""" Process an incoming RFC2822 email message, relying on
			``mail.message.parse()`` for the parsing operation,
			and ``message_route()`` to figure out the target model.

			Once the target model is known, its ``message_new`` method
			is called with the new message (if the thread record did not exist)
			or its ``message_update`` method (if it did).

		   :param string model: the fallback model to use if the message
			   does not match any of the currently configured mail aliases
			   (may be None if a matching alias is supposed to be present)
		   :param message: source of the RFC2822 message
		   :type message: string or xmlrpclib.Binary
		   :type dict custom_values: optional dictionary of field values
				to pass to ``message_new`` if a new record needs to be created.
				Ignored if the thread record already exists, and also if a
				matching mail.alias was found (aliases define their own defaults)
		   :param bool save_original: whether to keep a copy of the original
				email source attached to the message after it is imported.
		   :param bool strip_attachments: whether to strip all attachments
				before processing the message, in order to save some space.
		   :param int thread_id: optional ID of the record/thread from ``model``
			   to which this mail should be attached. When provided, this
			   overrides the automatic detection based on the message
			   headers.
		"""
		if model != 'electronic.voucher.supplier':
			return super(MailThreadInherit, self).message_process(model, message, custom_values, save_original, strip_attachments, thread_id)

		# extract message bytes - we are forced to pass the message as binary because
		# we don't know its encoding until we parse its headers and hence can't
		# convert it to utf-8 for transport between the mailgate script and here.
		if isinstance(message, xmlrpclib.Binary):
			message = bytes(message.data)
		if isinstance(message, str):
			message = message.encode('utf-8')
		message = email.message_from_bytes(message, policy=email.policy.SMTP)

		# parse the message, verify we are not in a loop by checking message_id is not duplicated
		msg_dict = self.message_parse(message, save_original=save_original)

		########## Codigo adicional FE ###############
		electronic_voucher = self.env['electronic.voucher.supplier']
		attachments = msg_dict.get('attachments')
		validate_xml = False
		for attachment in attachments:
			try:
				name = str(attachment.fname).lower()
				if name.find(".xml") >= 0:
					content = attachment.content

					# Aveces el odoo lo devuelve en str o b'
					if type(content) is str:
						content = content.encode()

					xml_base64 = base64.b64encode(content)

					dic = electronic_voucher._validate_charge_email(xml_base64)
					if dic and dic.get('warning', False):
						_logger.info('Xml invalido: ' + str(dic.get('warning', False)))
					else:
						validate_xml = True
			except:
				msg = 'Error al leer el xml, Contenido: \n' + str(attachment.content) + '\nError python: ' + str(sys.exc_info()) + "\nNombre de archivo: " + str(attachment.fname)
				_logger.info(msg)

		if not validate_xml:
			_logger.info('El correo no contiene una FE valida para ser cargada en CE, Asunto: %s' % str(msg_dict.get('subject')))
			return False
		else:
			_logger.info('Correo electrónico validado, el xml cumple con la estructura de FE, Asunto: %s' % str(msg_dict.get('subject')))

		########## Codigo adicional FE ###############

		if strip_attachments:
			msg_dict.pop('attachments', None)

		existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg_dict['message_id'])], limit=1)
		########## Codigo adicional FE ###############
		if existing_msg_ids and not validate_xml:
			########## Codigo adicional FE ###############
			_logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
				msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
			return False

		# find possible routes for the message
		routes = self.message_route(message, msg_dict, model, thread_id, custom_values)
		thread_id = self._message_route_process(message, msg_dict, routes)
		return thread_id
