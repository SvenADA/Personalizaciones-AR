# -*- coding: utf-8 -*-

import requests
import logging
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import time

_logger = logging.getLogger(__name__)

urls = {
	'prodBASE_URL': "https://api.comprobanteselectronicos.go.cr/recepcion/v1/",
	'prodAUTH_URL': "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token",
	'prodCLIENT_ID': "api-prod",

	'stagBASE_URL': "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/",
	'stagAUTH_URL': "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token",
	'stagCLIENT_ID': "api-stag"
}

global concurrency_token
concurrency_token = dict()


class TokenTemp:
	token_temp = None
	token_time = None
	refresh_token_temp = None
	token_used = False
	in_transaction = False
	expires_in = 0
	refresh_expires_in = 0

	def refresh_token(self, config, company_id):
		if config.mode_debug:
			_logger.info('\n---------------------------------\nRefrescando Token\n---------------------------------\n')

		headers = {'Content-type': 'application/x-www-form-urlencoded'}

		data = {
			"client_id": company_id.get_url('CLIENT_ID'),
			"refresh_token": self.refresh_token_temp,
			"grant_type": 'refresh_token'
		}

		response = requests.post(company_id.get_url('AUTH_URL'), data=data, headers=headers)

		if config.mode_debug:
			_logger.info('\n---------------------------------\nRefrescando Token, Codigo: ' + str(response.status_code) + '\n---------------------------------\n')

		if int(response.status_code) == 200:
			result = response.json()
			self.token_temp = "bearer " + result.get('access_token')
			self.refresh_token_temp = result.get('refresh_token')
			self.expires_in = int(result.get('expires_in')) / 60
			self.refresh_expires_in = int(result.get('refresh_expires_in')) / 60
			return True
		else:
			if config.mode_debug:
				_logger.info('\n---------------------------------\nRespuesta: ' + str(response._content) + '\n---------------------------------\n')
			self.token_used = False
			return self.get_token(config, company_id)

	def get_token(self, config, company_id):

		if self.token_used:
			return self.refresh_token(config, company_id)
		else:

			if config.mode_debug:
				_logger.info('\n---------------------------------\nObteniendo el Token\n---------------------------------\n')

			headers = {'Content-type': 'application/x-www-form-urlencoded'}

			data = {
				"client_id": company_id.get_url('CLIENT_ID'),
				"username": company_id.frm_ws_identificador,
				"password": company_id.frm_ws_password,
				"grant_type": "password"
			}

			response = requests.post(company_id.get_url('AUTH_URL'), data=data, headers=headers)

			if config.mode_debug:
				_logger.info('\n---------------------------------\nObteniendo el Token, Codigo: ' + str(response.status_code) + '\n---------------------------------\n')

			if int(response.status_code) == 200:
				result = response.json()
				self.token_temp = "bearer " + result.get('access_token')
				self.refresh_token_temp = result.get('refresh_token')
				self.expires_in = int(result.get('expires_in')) / 60
				self.refresh_expires_in = int(result.get('refresh_expires_in')) / 60
				self.token_used = True
				return True
			else:
				if config.mode_debug:
					_logger.info('\n---------------------------------\nRespuesta: ' + str(response._content) + '\n---------------------------------\n')
				return False


class CompanyElectronicMH(models.Model):
	_inherit = 'res.company'

	def get_url(self, url):
		return urls[self.frm_ws_ambiente + url]

	def get_token_object(self):
		key = str(self.id) + self.env.cr.dbname
		if key in concurrency_token:
			token_object = concurrency_token.get(key)
		else:
			config = self.get_config()
			token_object = TokenTemp()
			concurrency_token.update({
				key: token_object
			})
			token_object.token_time = datetime.now()
			token_object.get_token(config, self)

		return token_object

	def get_token_temp(self):

		config = self.get_config()

		token_object = self.get_token_object()

		if not token_object.in_transaction:
			now = datetime.now()
			expires_in = token_object.token_time + timedelta(minutes=token_object.expires_in)
			refresh_expires_in = token_object.token_time + timedelta(minutes=token_object.refresh_expires_in)
			if now >= expires_in:
				# Evitar error de concurrencia por los crons y obtenerlo solo una vez
				token_object.in_transaction = True
				if now >= refresh_expires_in:
					token_object.token_used = False
				token_object.token_time = now
				token_object.get_token(config, self)
				token_object.in_transaction = False
		else:
			time_sleep = 0.5
			sleep = 15
			sum_sleep = 0
			while sum_sleep <= sleep and token_object.in_transaction:
				time.sleep(time_sleep)
				sum_sleep += time_sleep
		return token_object.token_temp

	def check_connection(self):
		config = self.get_config()
		token_object = self.get_token_object()
		if token_object.get_token(config, self):
			title = "Conexión satisfactoria!"
			message = "Se obtuvo respuesta del Ministerio de Hacienda al obtener el inicio de sesión"
		else:
			title = "Conexión fallida!"
			message = "Por favor verificar la cuenta de usuario y clave, si el problema persiste verificar los servicios del Ministerio de Hacienda"

		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': title,
				'message': message,
				'sticky': False,
			}
		}
