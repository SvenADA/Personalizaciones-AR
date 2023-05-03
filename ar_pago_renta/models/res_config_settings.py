from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_cr_primer_limite = fields.Float(
        "Primer límite", related="company_id.l10n_cr_primer_limite", digits="Payroll", readonly=False
    )
    l10n_cr_segundo_limite = fields.Float(
        "Segundo límite", related="company_id.l10n_cr_segundo_limite", digits="Payroll", readonly=False
    )
    l10n_cr_tercer_limite = fields.Float(
        "Tercer límite", related="company_id.l10n_cr_tercer_limite", digits="Payroll", readonly=False
    )
    l10n_cr_cuarto_limite = fields.Float(
        "Cuarto límite", related="company_id.l10n_cr_cuarto_limite", digits="Payroll", readonly=False
    )
    l10n_cr_monto_por_hijo = fields.Float(
        "Monto por hijo", related="company_id.l10n_cr_monto_por_hijo", digits="Payroll", readonly=False
    )
    l10n_cr_monto_por_conyuge = fields.Float(
        "Monto por esposa", related="company_id.l10n_cr_monto_por_conyuge", digits="Payroll", readonly=False
    )

    l10n_cr_ccss = fields.Float("Porcentaje de CCSS para trabajadores", related="company_id.l10n_cr_ccss", readonly=False)
    l10n_cr_bpdc = fields.Float("Porcentaje de BPDC para trabajadores", related="company_id.l10n_cr_bpdc", readonly=False)
    l10n_cr_asociacion_solidarista = fields.Float(
        "Porcentaje Asociación Solidarista", related="company_id.l10n_cr_asociacion_solidarista", readonly=False
    )
    l10n_cr_ccss_patrono = fields.Float("Porcentaje de CCSS para patrono", related="company_id.l10n_cr_ccss_patrono",
                                readonly=False)
    l10n_cr_bpdc_patrono = fields.Float("Porcentaje de BPDC para patrono", related="company_id.l10n_cr_bpdc_patrono",
                                readonly=False)

    l10n_cr_ins_email = fields.Char(
        "Email", related="company_id.l10n_cr_ins_email", readonly=False, help="Value to be used in the INS file."
    )
    l10n_cr_ins_number = fields.Char("Number", related="company_id.l10n_cr_ins_number", readonly=False)
    l10n_cr_ins_fax = fields.Char("Fax", related="company_id.l10n_cr_ins_fax", readonly=False)
    l10n_cr_ins_header = fields.Char(
        "Header", related="company_id.l10n_cr_ins_header", readonly=False, help="Header for TXT in INS file."
    )
    l10n_cr_retroactive_payment = fields.Boolean(
        "Retroactively pay salary changes?",
        related="company_id.l10n_cr_retroactive_payment",
        readonly=False,
        help="If checked, the employee will receive retroactive for annual salary increase.",
    )
    l10n_cr_holidays_provision = fields.Boolean(
        "Apply Holiday Provision?",
        related="company_id.l10n_cr_holidays_provision",
        readonly=False,
        help="If it is checked, a holiday provision will be saved. A proportional amount will be saved in each "
        "payslip through a company contribution. This amount will be used to pay employee's vacations when they "
        "enjoy them.",
    )
    l10n_cr_pay_wage_from_changes_date = fields.Boolean(
        "Pay salary changes from the date of the change?",
        related="company_id.l10n_cr_pay_wage_from_changes_date",
        readonly=False,
        help="If it is checked, when an employee receives a salary change, that wage will start to be paid from "
        "the date the changes was made.",
    )
    l10n_cr_edi_days_daily_wage = fields.Float(
        "Days for Daily Wage CR",
        readonly=False,
        related="company_id.l10n_cr_edi_days_daily_wage",
        help="Number of days to consider in the daily wage for the employees",
    )
