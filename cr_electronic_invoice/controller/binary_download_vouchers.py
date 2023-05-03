from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition
import base64
import shutil
import os
import time
from pathlib import Path
from datetime import datetime
import pytz

class BinaryDownloadVouchers(http.Controller):

    @http.route('/web/binary/account_invoice_download_vouchers', type='http', auth="user")
    def account_invoice_download_vouchers(self, ids, **kw):
        ids = ids[1:-1].split(',')
        folder_path = '/tmp/xmls' + str(time.time())
        os.mkdir(folder_path)
        invoices = request.env['account.move'].search([('id', 'in', ids)])
        try:
            for inv in invoices:
                if inv.xml_comprobante or inv.xml_respuesta_tributacion:
                    folder_path_fe = folder_path + '/' + inv.number_electronic
                    os.mkdir(folder_path_fe)
                    # FE
                    if inv.xml_comprobante:
                        name = inv.fname_xml_comprobante
                        filecontent = base64.b64decode(inv.xml_comprobante or '')
                        file = open(folder_path_fe + '/' + name, "w")
                        file.write(filecontent.decode("utf-8"))
                        file.close()
                    # Mejade MH
                    if inv.xml_respuesta_tributacion:
                        name = inv.fname_xml_respuesta_tributacion
                        filecontent = base64.b64decode(inv.xml_respuesta_tributacion or '')
                        file = open(folder_path_fe + '/' + name, "w")
                        file.write(filecontent.decode("utf-8"))
                        file.close()

                    # FE PDF
                    # Se extrae el pdf de la factura
                    name = inv.get_type_name_pdf(inv) + inv.number_electronic + '.pdf'
                    attachment_pdf = request.env['ir.attachment'].search([
                        ('res_model', '=', 'account.move'),
                        ('res_id', '=', inv.id),
                        ('name', '=', name)
                    ], limit=1)

                    if attachment_pdf:
                        filecontent = base64.b64decode(attachment_pdf.datas or '')
                        filename = Path(folder_path_fe + '/' + name)
                        filename.write_bytes(filecontent)

            shutil.make_archive(folder_path, 'zip', folder_path, base_dir=None)
            zipFile = open(folder_path + '.zip', "rb").read()
            shutil.rmtree(folder_path, ignore_errors=True)
            os.remove(folder_path + '.zip')

            now_utc = datetime.now(pytz.timezone('UTC'))
            now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))

            return request.make_response(zipFile, [
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', content_disposition('FE-Comprobantes-' + str(now_cr.date()) + '.zip'))
            ])
        
        except Exception as e:
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            res = request.make_response(html_escape(json.dumps(error)))
            raise InternalServerError(response=res) from e
