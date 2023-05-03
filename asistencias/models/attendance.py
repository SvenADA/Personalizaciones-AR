from odoo import _,fields, models, api, tools
from odoo.exceptions import ValidationError
import csv

class asistencias(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance']

    with open('/home/ada/Documentos/ODOO/odoo-14.0/custom/addons/asistencias/data/provincias.csv', 'r') as provincia_csv:
        provincia_reader = csv.reader(provincia_csv, delimiter=',')
        provincia_count = 0
        lista_provincias = []
        for row in provincia_reader:
            if provincia_count == 0:
                print(f'Column names are {", ".join(row)}')
                provincia_count += 1
            else:
                lista_provincias.append(row[1])
                print(f'\t{row[0]} Codigo de la provincia {row[1]}.')
                provincia_count += 1
        print(f'Processed {provincia_count} lines.')
        print(lista_provincias, ' Provincias')

    with open('/home/ada/Documentos/ODOO/odoo-14.0/custom/addons/asistencias/data/cantones.csv', 'r') as canton_csv:
        canton_reader = csv.reader(canton_csv, delimiter=',')
        canton_count = 0
        lista_cantones = []
        for row in canton_reader:
            if canton_count == 0:
                print(f'Column names are {", ".join(row)}')
                canton_count += 1
            else:
                lista_cantones.append(row[1])
                print(f'\t{row[0]} Codigo del canton {row[1]}.')
                canton_count += 1
        print(f'Processed {canton_count} lines.')
        print(lista_cantones, ' Cantones')

    with open('/home/ada/Documentos/ODOO/odoo-14.0/custom/addons/asistencias/data/distritos.csv', 'r') as distrito_csv:
        distrito_reader = csv.reader(distrito_csv, delimiter=',')
        distrito_count = 0
        lista_distrito = []
        for row in distrito_reader:
            if distrito_count == 0:
                print(f'Column names are {", ".join(row)}')
                distrito_count += 1
            else:
                lista_distrito.append(row[1])
                print(f'\t{row[0]} Codigo del distrito {row[1]}.')
                distrito_count += 1
        print(f'Processed {distrito_count} lines.')
        print(lista_distrito, ' Distritos')

    provincia = fields.Selection(string="Provincia", selection=[('1', 'San José'),
                                                                ('2', 'Alajuela'),
                                                                ('3', 'Cartago'),
                                                                ('4', 'Heredia'),
                                                                ('5', 'Guanacaste'),
                                                                ('6', 'Puntarenas'),
                                                                ('7', 'Limón')])
    canton = fields.Selection(string="Canton", selection=[('type1', 'Type 1'),('type2', 'Type 2'),])
    distrito = fields.Selection(string="Distrito", selection=[('type1', 'Type 1'),('type2', 'Type 2'),])
    direccion = fields.Char(string="Dirección")