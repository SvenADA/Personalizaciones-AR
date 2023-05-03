# -*- coding: utf-8 -*-
##############################################################################
#	Odoo Proprietary License v1.0
#	Copyright (c) 2019 Delfix Tecnosoluciones S.A. (http://www.delfixcr.com) All Rights Reserved.
##############################################################################

import logging
from odoo import models, fields, api, _
import sys
import subprocess
from odoo.service import server
from cryptography.fernet import Fernet

key = b'z870TAOgljNThUcAdE54WbBB6nF3WRoBwlg7_OJoWFs='

_logger = logging.getLogger(__name__)


class ReportAgedPartnerBalance(models.AbstractModel):
    _name = 'remote.update'
    _description = 'Actualización remota de Facturación Electrónica'

    def _get_encrypt(self, message):
        f = Fernet(key)
        encrypted = f.encrypt(message)
        return encrypted

    def _get_decrypt(self, message):
        f = Fernet(key)
        decrypted = f.decrypt(message)
        return decrypted

    @api.model
    def update_repository_fe(self, args):
        _logger.info('\n---------------------------------\n' + 'Iniciando actualizacion de repositorios')

        log = ''

        user_git = str(args.get('user_git')).encode()
        password_git = str(args.get('password_git')).encode()

        user_git = self._get_decrypt(user_git).decode()
        password_git = self._get_decrypt(password_git).decode()

        repositories = args.get('repositories')

        for repository in repositories:
            repository_name = repository.get('repository_name')
            path_git = repository.get('path_git')
            branch = repository.get('branch')

            log += str(repository.get('repository_name')) + '\n'

            command = 'cd ' + path_git + ';' + 'git log -1'
            output = subprocess.getoutput(command)
            log += '\n' + 'Commit actual: \n' + str(output) + '\n\n'
            _logger.info('\n---------------------------------\n' + 'Version actual: ' + str(output) + '\n---------------------------------\n')

            command = 'cd ' + path_git + ';' + 'git reset --hard'
            output = subprocess.getoutput(command)
            # log += str(output) + '\n'
            _logger.info('\n---------------------------------\n' + 'Restaurando GIT: ' + str(output) + '\n---------------------------------\n')

            command = 'cd ' + path_git + ';' + 'git pull https://' + user_git + ':' + password_git + '@github.com/Delfix-CR/' + repository_name + '.git ' + branch
            output = subprocess.getoutput(command)
            log += 'Archivos afectados: \n' + str(output) + '\n\n'
            _logger.info('\n---------------------------------\n' + 'Descargando cambios del GIT' + str(output) + '\n---------------------------------\n')

            command = 'cd ' + path_git + ';' + 'git log -1'
            output = subprocess.getoutput(command)
            log += 'Último commit agregado: \n' + str(output) + '\n\n'

            command = 'history -c'
            subprocess.getoutput(command)

        return {'output': log}

    @api.model
    def restart_server(self, args):
        _logger.info('\n---------------------------------\n' + 'Reiniciando Servidor' + '\n---------------------------------\n')
        server.restart()
        return {'output': 'Servidor reiniciado'}

    @api.model
    def update_server_fe(self, args):
        _logger.info('\n---------------------------------\n' + 'Inicio de actualizacion remota Modulo: ' + str(args.get('technical_name')) + '\n---------------------------------\n')

        module = self.env['ir.module.module'].search([
            ('name', 'in', args.get('technical_name'))
        ])

        output = str(args.get('technical_name')) + '     (: Módulo actualizado con éxito'
        try:
            module.button_immediate_upgrade()
        except:
            output = str(args.get('technical_name')) + '   ): Ocurrió un error al actualizar el modulo, por favor atender manualmente el problema.\n\n'
            output += str(sys.exc_info())

        _logger.info('\n---------------------------------\n' + 'Estado de actualizacion: ' + str(output))
        return {'output': str(output)}
