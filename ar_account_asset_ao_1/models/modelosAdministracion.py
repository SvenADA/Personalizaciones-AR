from odoo import models, fields, _, api

#Creando un modelo (tabla de la base de datos) a partir de una clases

class ModelosAdministracion(models.Model):

    _inherit = ['account.asset']
    
    #Nombre de los campos
    
    responsable = fields.Char(string='Responsable a Cargo')