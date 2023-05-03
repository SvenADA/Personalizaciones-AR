# -*- coding:utf-8 -*-

from odoo import _,fields, models, api, tools
from odoo.exceptions import ValidationError
from datetime import datetime

class Renta(models.Model):
    _inherit = 'hr.contract'

    first_wage = fields.Monetary(string="Primer quincena")
    second_wage = fields.Monetary(string="Segunda quincena")
    inabilty_days = fields.Integer(string="Días de incapacidad")
    commission = fields.Monetary(string="Comisión")
    xmas_bonus = fields.Monetary(string="Aguinaldo")
    bank_account = fields.Char(string="Cuenta bancaria")

Renta()

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    salario_devengado = fields.Monetary(compute='_compute_rent')
    asociacion_colaborador = fields.Monetary(compute='_compute_aso_colaborador')
    asociacion_patronal = fields.Monetary(compute='_compute_aso_patro')
    aguinaldo = fields.Monetary(compute='_compute_xmas_bonus')
    dias_de_incapacidad = fields.Integer(compute='_compute_days')

    def _compute_rent(self):
        for payslip in self:
            payslip.salario_devengado = payslip._get_salary_line('BRUTO')

    def _compute_days(self):
        for payslip in self:
            payslip.dias_de_incapacidad = payslip._get_inc_days()

    def _compute_aso_colaborador(self):
        for payslip in self:
            payslip.asociacion_colaborador = payslip._get_salary_line('P013')

    def _compute_aso_patro(self):
        for payslip in self:
            payslip.asociacion_patronal = payslip._get_salary_line('P290')

    def _compute_xmas_bonus(self):
        for payslip in self:
            payslip.aguinaldo = payslip._get_salary_line('AGUINALDO')

    def _get_salary_line(self, code):
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum([line.total for line in lines])

    def _get_inc_days(self):
        work = self.worked_days_line_ids.filtered(lambda worked_days: worked_days.work_entry_type_id.name == 'Ausencia por incapacidad')
        return sum([worked_days.number_of_days for worked_days in work])

    # ______________________BOTÓN CALCULAR RENTA EN RECIBO DE SALARIO_________________________#

    def action_calculate_rent(self):
        day_slip = int(self.date_to.strftime('%d'))
        month_slip = int(self.date_to.strftime('%m'))

        for rec in self:
            employee = rec.employee_id.name
            net_salary = rec.salario_devengado
            xmas_wage = rec.aguinaldo
            struct = rec.struct_id.name
            recordUpdate = rec.env['hr.contract'].search([('employee_id', '=', employee)])

            record_leave = rec.env['hr.leave'].search([('employee_id', '=', employee), ('date_to', '>=', self.date_to)])
            print(record_leave.exists())

        if not record_leave:
            recordUpdate.write({"inabilty_days": 0})

        if record_leave.exists() and recordUpdate.exists():
            month_start = int(record_leave.date_from.strftime('%m'))
            month_to = int(record_leave.date_to.strftime('%m'))
            day_start = int(record_leave.date_from.strftime('%d'))
            day_to = int(record_leave.date_to.strftime('%d'))
            duration = record_leave.duration_display.split(" ")
            duration = int(duration[0])

            if month_slip == month_to and month_slip >= month_start:
                if day_start <= day_slip and day_to > day_slip:
                    work = self.worked_days_line_ids.filtered(lambda worked_days: worked_days.work_entry_type_id.name == 'Incapacidad')
                    days = sum([worked_days.number_of_days for worked_days in work])
                    recordUpdate.write({"inabilty_days": days})

            if month_start <= month_slip and month_to > month_slip:
                work = self.worked_days_line_ids.filtered(lambda worked_days: worked_days.work_entry_type_id.name == 'Incapacidad')
                days = sum([worked_days.number_of_days for worked_days in work])
                recordUpdate.write({"inabilty_days": days})

        # ________________Cálculo de renta en la estructura comisiones_________________#
        if struct == "Comisiones":
            if recordUpdate.exists():
                recordUpdate.write({"commission": net_salary})
                recordUpdate.write({"xmas_bonus": xmas_wage + recordUpdate.xmas_bonus})

        # ________________Cálculo de renta en la estructura de planilla normal_________________#
        if struct == "Costa Rica":
            if recordUpdate.exists():
                recordUpdate.write({"xmas_bonus": xmas_wage + recordUpdate.xmas_bonus})

                if day_slip > 11 and day_slip < 20:
                    recordUpdate.write({"first_wage": net_salary})
                    title = _("Renta calculada")
                    message = _("Los datos han sido guardados en el contrato del empleado")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': title,
                            'message': message,
                            'sticky': False,
                        }
                    }
                if day_slip > 26 and day_slip <= 31:
                    recordUpdate.write({"second_wage": net_salary})
                    title = _("Renta calculada")
                    message = _("Los datos han sido guardados en el contrato del empleado")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': title,
                            'message': message,
                            'sticky': False,
                        }
                    }

        # ________________Reinicio del aguinaldo_________________#
        if struct == "Aguinaldo":
            if month_slip == "12":
                recordUpdate.write({"xmas_bonus": "0"})

    # ______________________BOTÓN CALCULAR RENTA EN VISTA DE LISTA TO DO_________________________#

    def action_calculate_rent_tree(self):
        employee_ids = self.env['hr.payslip'].browse(self.env.context.get('active_ids'))
        print(employee_ids, 'Id del employee')

        day = int(self.date_to.strftime('%d'))

        for rec in employee_ids:
            employee = rec.employee_id.name
            net_salary = rec.salario_devengado
            recordUpdate = rec.env['hr.contract'].search([('employee_id', '=', employee)])

            if day > 11 and day < 20:
                if recordUpdate.exists():
                    recordUpdate.write({"first_wage": net_salary})
                    title = _("Renta calculada")
                    message = _("Los datos han sido guardados en el contrato del empleado")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': title,
                            'message': message,
                            'sticky': False,
                        }
                    }
            if day > 26 and day <= 31:
                if recordUpdate.exists():
                    recordUpdate.write({"second_wage": net_salary})
                    title = _("Renta calculada")
                    message = _("Los datos han sido guardados en el contrato del empleado")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': title,
                            'message': message,
                            'sticky': False,
                        }
                    }

HrPayslip()

class HrPayslipBatch(models.Model):
    _inherit = "hr.payslip.run"

    # ______________________BOTÓN CALCULAR RENTA EN LOTES_________________________#

    def action_calculate_rent_batch(self):
        day_slip = int(self.date_end.strftime('%d'))
        month_slip = int(self.date_end.strftime('%m'))
        list = self.env['hr.payslip'].search([('date_to', '=', self.date_end)])

        for rec in list:
            employee = rec.employee_id.name
            net_salary = rec.salario_devengado
            xmas_wage = rec.aguinaldo
            days_inability = rec.dias_de_incapacidad
            struct = rec.struct_id.name
            recordUpdate = rec.env['hr.contract'].search([('employee_id', '=', employee)])
            record_leave = rec.env['hr.leave'].search([('employee_id', '=', employee), ('date_to', '>=', self.date_end)])

            if struct == "Comisiones":
                if recordUpdate.exists():
                    recordUpdate.write({"xmas_bonus": xmas_wage + recordUpdate.xmas_bonus})
                    recordUpdate.write({"commission": net_salary})

            if struct == "Costa Rica":
                if recordUpdate.exists():
                    recordUpdate.write({"xmas_bonus": xmas_wage + recordUpdate.xmas_bonus})

                    if not record_leave:
                        recordUpdate.write({"inabilty_days": 0})

                    if record_leave.exists():
                        month_start = int(record_leave.date_from.strftime('%m'))
                        month_to = int(record_leave.date_to.strftime('%m'))
                        day_start = int(record_leave.date_from.strftime('%d'))
                        day_to = int(record_leave.date_to.strftime('%d'))
                        duration = record_leave.duration_display.split(" ")
                        duration = int(duration[0])

                        if month_slip == month_to and month_slip == month_start:
                            if day_start <= day_slip and day_to > day_slip:
                                recordUpdate.write({"inabilty_days": days_inability})

                        if month_start <= month_slip and month_to > month_slip:
                            print(days_inability)
                            recordUpdate.write({"inabilty_days": days_inability})

                    if day_slip > 11 and day_slip < 20:
                        recordUpdate.write({"first_wage": net_salary})
                        title = _("Renta calculada")
                        message = _("Los datos han sido guardados en el contrato de los empleados")
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': title,
                                'message': message,
                                'sticky': False,
                            }
                        }
                    if day_slip > 26 and day_slip <= 31:
                        recordUpdate.write({"second_wage": net_salary})
                        title = _("Renta calculada")
                        message = _("Los datos han sido guardados en el contrato de los empleados")
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': title,
                                'message': message,
                                'sticky': False,
                            }
                        }

HrPayslipBatch()

