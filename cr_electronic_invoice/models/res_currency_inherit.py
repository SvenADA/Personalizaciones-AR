from odoo import models, fields, api
import time
import logging
import json
import requests
from datetime import datetime
import xml.etree.ElementTree as ET
import pytz
import re

_logger = logging.getLogger(__name__)


class UpdateExchangeRate(models.Model):
	_inherit = 'res.currency'

	def get_dollar_central_bank(self, currency_iso):

		indicador = currency_iso == 'USD' and '318' or '333'

		now_utc = datetime.now(pytz.timezone('UTC'))
		now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
		date = now_cr.strftime("%d/%m/%Y")
		url_get = 'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML?' + \
		          'Indicador=' + indicador + \
		          '&FechaInicio=' + str(date) + \
		          '&FechaFinal=' + str(date) + \
		          '&Nombre=' + 'Delfix' + \
		          '&SubNiveles=n' + \
		          '&CorreoElectronico=' + 'desarrollo@delfixcr.com' + \
		          '&Token=' + '2ROERLFC3E'

		try:
			reponse = requests.get(url_get)
		except:
			_logger.info('\n---------------------------------\nError al obtener tipo de cambio (Banco Central)\n---------------------------------\n')
			return False
		if reponse.status_code == 200:
			xml = reponse.content.decode()
			xml = re.sub(' xmlns="[^"]+"', '', xml, count=1)
			root = ET.fromstring(xml)
			root = ET.fromstring(root.text)
			for child in root.iter('*'):
				if child.tag == 'NUM_VALOR':
					return child.text
		else:
			_logger.info('\n---------------------------------\nError al obtener tipo de cambio (Banco Central)' + str(reponse) + '\n---------------------------------\n')
			return False

	def get_dollar_mh(self, currency_iso):
		url = currency_iso == 'USD' and 'https://api.hacienda.go.cr/indicadores/tc/dolar' or 'https://api.hacienda.go.cr/indicadores/tc/euro'

		try:
			response_document = requests.get(url, verify=False)
		except:
			_logger.info('\n---------------------------------\nError al obtener tipo de cambio (MH)\n---------------------------------\n')
			return False
		response_content = json.loads(str(response_document._content, 'utf-8'))
		if response_document.status_code == 200:
			if currency_iso == 'USD':
				return response_content.get('venta').get('valor')
			else:
				return response_content.get('dolares')
		else:
			_logger.info('\n---------------------------------\nError al obtener tipo de cambio (MH)' + str(response_content) + '\n---------------------------------\n')
			return False

	def get_dollar_exchange_rate(self, currency_iso):
		return self.get_dollar_central_bank(currency_iso) or self.get_dollar_mh(currency_iso)

	@api.model
	def _update_exchange_rate(self, retry=0):
		date = fields.Date.today()

		currency_list = ['USD', 'EUR']
		company_ids = self.env['res.company'].search([])

		rate_usd = 0

		for currency_iso in currency_list:
			currency_id = self.env['res.currency'].search([('name', '=', currency_iso), ('active', '=', True)], limit=1)
			if currency_id:
				rate = self.get_dollar_exchange_rate(currency_iso)

				if rate:
					rate = float(rate)
					# El BCCR devuelve el tipo de cambio en dolares
					if currency_iso == 'USD':
						rate_usd = rate

					for company_id in company_ids:
						if company_id.currency_used:
							self.env['res.currency.rate'].create({
								'name': date,
								'rate': 1 / (currency_iso == 'EUR' and rate * rate_usd or rate),
								'currency_id': currency_id.id,
								'company_id': company_id.id,
							})
						else:
							# Solo si se utiliza 1 modena adicinal
							currency_crc = self.env['res.currency'].search([('name', '=', 'CRC')], limit=1)
							self.env['res.currency.rate'].create({
								'name': date,
								'rate': float(rate),
								'currency_id': currency_crc.id,
								'company_id': company_id.id,
							})
				elif retry < 3:
					time.sleep(10)
					self._update_exchange_rate(retry=retry + 1)