from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_cr_primer_limite = fields.Float(digits="Payroll")
    l10n_cr_segundo_limite = fields.Float(digits="Payroll")
    l10n_cr_tercer_limite = fields.Float(digits="Payroll")
    l10n_cr_cuarto_limite = fields.Float(digits="Payroll")
    l10n_cr_monto_por_hijo = fields.Float(digits="Payroll")
    l10n_cr_monto_por_conyuge = fields.Float(digits="Payroll")
    l10n_cr_ccss = fields.Float("Porcentaje de CCSS para trabajadores")
    l10n_cr_bpdc = fields.Float("Porcentaje de BPDC para trabajadores")
    l10n_cr_ccss_patrono = fields.Float("Porcentaje de CCSS del patrono")
    l10n_cr_bpdc_patrono = fields.Float("Porcentaje de BPDC del patrono")
    l10n_cr_asociacion_solidarista = fields.Float("Working ASOCIACIÓN SOLIDARISTA%")
    l10n_cr_ins_email = fields.Char(help="Value to be used in the INS file.")
    l10n_cr_ins_header = fields.Char("Header", help="Header for TXT in INS file.")
    l10n_cr_ins_number = fields.Char("Number")
    l10n_cr_ins_fax = fields.Char("Fax")
    l10n_cr_retroactive_payment = fields.Boolean(
        "Retroactively pay salary changes?",
        help="If checked, the employee will receive retroactive for annual salary increase.",
    )
    l10n_cr_holidays_provision = fields.Boolean(
        "Apply Holiday Provision?",
        help="If it is checked, a holiday provision will be saved. A proportional amount will be saved in each "
        "payslip through a company contribution. This amount will be used to pay employee's vacations when they "
        "enjoy them.",
    )
    l10n_cr_pay_wage_from_changes_date = fields.Boolean(
        "Pay salary changes from the date of the change?",
        help="If it is checked, when an employee receives a salary change, that wage will start to be paid from "
        "the date the changes was made.",
    )
    l10n_cr_edi_days_daily_wage = fields.Float(
        "Days for Daily Wage CR", default=30.0, help="Number of days to consider in the daily wage for the employees"
    )
