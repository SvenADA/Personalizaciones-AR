from datetime import date

from odoo import models, fields, api, _

#Creando un modelo (tabla de la base de datos) a partir de una clase

class SolicitudAdmision(models.Model):

    _name = 'solicitud_admision'  # Nombre de la tabla que se va a generar
    _description = "Solicitud de Admision"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    num_identificacion = fields.Char(string="Número de Indentificación", index=True, copy=False)
    nombre = fields.Char(string="Nombre completo (s)")
    primer_apellido = fields.Char(string="Primer Apellido")
    segundo_apellido = fields.Char(string="Segundo Apellido")
    fecha_nacimiento = fields.Date(string="Fecha de Nacimiento", default=date.today())
    genero = fields.Selection([
        ('M', 'Masculino'),
        ('F', 'Femenino')
    ], string='Genero', default='')

    patrono = fields.Char(string="Patrono")
    actividad_empresa = fields.Text(string="Actividad de la Empresa")
    puesto = fields.Char(string="Puesto Actual")
    ingreso_bruto = fields.Float(string="Ingreso Bruto Mensual ₡")
    ingreso_liquido = fields.Float(string="Ingreso Líquido Mensual ₡")

class HelpdeskAdmision(models.Model):

    _inherit = ['helpdesk.ticket']

    def button_action_form(self):
        return {
            'name': _('Solicitud Admisión'),
            'view_mode': 'tree,form',
            'res_model': 'solicitud_admision',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    '''Función para mostrar un pop up de la plantilla de correo'''
    def send_form_email(self):

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('form_send', False):
                template_id = ir_model_data._xmlid_lookup('template_email_form')[2]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'helpdesk.ticket',
            'active_model': 'helpdesk.ticket',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        # In the case of a RFQ or a PO, we want the "View..." button in line with the state of the
        # object. Therefore, we pass the model description in the context, in the language in which
        # the template is rendered.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

class custom_popup(models.TransientModel):
    _inherit = ['mail.compose.message']

    note = fields.Text(string="Nota")
    share_link = fields.Char(string="Share link", default='https://playa-bonita-desarrollo-1-5641737.dev.odoo.com/request')

