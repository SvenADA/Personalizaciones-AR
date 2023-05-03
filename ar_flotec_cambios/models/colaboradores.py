# -*- coding:utf-8 -*-

from odoo import _,fields, models, api, tools
from odoo.exceptions import ValidationError
from datetime import datetime

class contratos(models.Model):
    _inherit = 'hr.contract'

contratos()

class colaboradores(models.Model):
    _inherit = 'hr.employee'

    work_place = fields.Selection(string="Ubicación de trabajo", selection=[
        ('1', 'Oficina'),
        ('2', 'Ruta'),
        ('3', 'Mixta'),])

    certificate = fields.Selection(string="Nivel de estudio", selection_add=[
        ('high_school', 'Secundaria'),
        ('diplomat', 'Diplomado'),
        ('tecnician', 'Técnico'),
        ('bachelor', 'Bachiller universitario'),
        ('graduate', 'Licenciatura'),
        ('master', 'Maestría'),
        ('doctor', 'Doctorado'),
        ('other', 'Otro'),])

    gender = fields.Selection(string="Género", selection_add=[
        ('non_binary', 'No binario'),
        ('fluid_gender', 'Género fluido'),
        ('other', 'Otro'),])

colaboradores()
