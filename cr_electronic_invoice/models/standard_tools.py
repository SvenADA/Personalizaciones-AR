# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
import decimal
import base64
import re
import xml.etree.ElementTree as ET

phone_char = ('(', ')', ' ', '-', '+')


# https://kfolds.com/rounding-in-python-when-arithmetic-isnt-quite-right-11a79a30390a
# Redondeo Ej: 2.5 = 3, por defecto python es 2.5 = 2
def round_decimal(x, digits=0):
	# casting to string then converting to decimal
	x = decimal.Decimal(str(x))

	# rounding for integers
	if digits == 0:
		return int(x.quantize(decimal.Decimal("1"), rounding='ROUND_HALF_UP'))

	# string in scientific notation for significant digits: 1e^x
	if digits > 1:
		string = '1e' + str(-1 * digits)
	else:
		string = '1e' + str(-1 * digits)

	# rounding for floating points
	return float(x.quantize(decimal.Decimal(string), rounding='ROUND_HALF_UP'))


# Funciones reutilizables
def validate_identification(identification, code):
	number_digits = len(identification)
	validate_digits = True
	if code == '01':
		if number_digits != 9:
			return ('La identificación del cliente tipo Cédula física debe de contener 9 dígitos, sin cero al inicio y sin guiones.')
	if code == '02':
		if number_digits != 10:
			return ('La identificación del cliente tipo Cédula jurídica debe contener 10 dígitos, sin cero al inicio y sin guiones.')
	if code == '03':
		if number_digits < 11 or number_digits > 12:
			return ('La identificación del cliente tipo DIMEX debe contener 11 o 12 dígitos, sin ceros al inicio y sin guiones.')
	if code == '04':
		if number_digits != 10:
			return ('La identificación del cliente tipo NITE debe contener 10 dígitos, sin ceros al inicio y sin guiones.')
	if code == '05':
		validate_digits = False
		if number_digits > 20:
			return ('La identificación tipo Extranjero debe ser menor o igual a 20 caracteres alfanuméricos.')

		if not re.match("^[A-Za-z0-9]*$", identification):
			return ('La identificación tipo Extranjero solo debe contener caracteres alfanuméricos, sin espacios ni guiones.')

	if validate_digits:
		if not identification.isdigit():
			return ('La identificación del cliente debe ser numérica, sin cero al inicio y sin guiones')


# Elimina las letras de un string y solo deja los numeros
def delete_letters(numero):
	tem_numero = numero
	for char in numero:
		if not char.isdigit():
			tem_numero = tem_numero.replace(char, "")
	return tem_numero


# funciones para validar datos
def validate_whole_number(number):
	if number:
		return number.isdigit()
	else:
		return False


def validate_number_digits(number, digits):
	if len(number) == digits:
		return True
	else:
		return False


def validate_positivo(number):
	if int(number) >= 0:
		return True
	else:
		return False


def validate_email_structure(email):
	if re.match('^[(a-z0-9\_\-\.)]+@[(a-z0-9\_\-\.)]+\.[(a-z)]{2,15}$', email.lower()):
		return True
	else:
		return False


# Validaciones con respuestas
def validate_phone_code(phone_code):
	if not validate_whole_number(phone_code) or not validate_positivo(phone_code):
		return ("Por favor ingresar un código numérico de telefono sin guiones y sin espacios")


def validate_fax_code(fax_code):
	if not validate_whole_number(fax_code) or not validate_positivo(fax_code):
		return ("Por favor ingresar un código numérico de fax sin guiones y sin espacios")


def get_valid_phone(phone, phone_code):
	phone = phone or ''
	phone_char_temp = phone_char + (phone_code or '',)
	for char in phone_char_temp:
		phone = phone.replace(char, '')
	return phone


def validate_phone(phone):
	if phone:
		for char in phone_char:
			phone = phone.replace(char, '')
		if not validate_whole_number(phone) or not validate_positivo(phone):
			return ("Por favor ingrese un número de Teléfono válido")


def validate_fax(phone):
	if phone:
		for char in phone_char:
			phone = phone.replace(char, '')
		if not validate_whole_number(phone) or not validate_positivo(phone):
			return ("Por favor ingrese un número de Fax válido")


def validate_company_registry(company_registry):
	if not validate_whole_number(company_registry) or not validate_positivo(company_registry):
		return ("Por favor ingresar un numéro de registro de compañía sin guiones y sin espacios")


def validate_email(email):
	if email and not validate_email_structure(email):
		return ("El correo electrónico no cumple con una estructura válida")


def validate_mobil(mobil):
	if not validate_whole_number(mobil) or not validate_positivo(mobil):
		return ("Por favor ingresar un numéro de móvil sin guiones y sin espacios")


def validate_sucursal(sucursal):
	if sucursal:
		if not validate_whole_number(sucursal):
			raise ValidationError("Por favor ingresar un numero de sucursal entero")
		if not validate_positivo(sucursal):
			raise ValidationError("Por favor ingresar un numero de sucural positivo")
		if not validate_number_digits(sucursal, 3):
			raise ValidationError("Por favor ingresar un numero de sucursal con tres digitos")


def validate_terminal(terminal):
	if terminal:
		if not validate_whole_number(terminal):
			raise ValidationError("Por favor ingresar un numero de terminal entero")
		if not validate_positivo(terminal):
			raise ValidationError("Por favor ingresar un numero de terminal positivo")
		if not validate_number_digits(terminal, 5):
			raise ValidationError("Por favor ingresar un numero de terminal con cinco digitos")


# Toma el archivo xml como binario y lo parsea a string, ademas lo devuelve en formato listo para navegar como xml
def xml_supplier_to_ET(xml_supplier_approval):
	string_xml = base64.b64decode(xml_supplier_approval)  # se toma el binario y se pasa a string
	# Remplaza utf-8-sig Byte Order Marks (BOM), caracteres invalidos
	string_xml = string_xml.decode('ascii', 'ignore')
	# Se modifica el XML para quitar todos los xmlns
	string_xml_repl = re.sub(' xmlns="[^"]+"', '', string_xml)  # Remplaza xmlns por un vacio con "
	string_xml_repl = re.sub(" xmlns='[^']+'", '', string_xml_repl)  # Remplaza xmlns por un vacio con '
	root = ET.fromstring(string_xml_repl)  # parsea el xml para navegarlo
	return root


def replace_invalid_tokens(xml):
	# Elimina caracteres extrannos e invalidos para el XML
	remove_illegal = re.compile('[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
	xml = remove_illegal.sub('', xml)

	invalid_tokens = [
		("&", "&amp;"),
		(">", "&gt;"),
		("<", "&lt;"),
	]

	for token in invalid_tokens:
		xml = xml.replace(token[0], token[1])
	return xml
