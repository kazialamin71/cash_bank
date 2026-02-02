# -*- coding: utf-8 -*-
import json
import urllib

from openerp import models, fields, api
from openerp.exceptions import Warning


class CashBankBookWizard(models.TransientModel):
    _name = 'cash.bank.book.wizard'
    _description = 'Cash Flow & Bank Book Wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.user.company_id
    )

    target_move = fields.Selection([
        ('posted', 'Posted Entries Only'),
        ('all', 'All Entries'),
    ], default='all', required=True)

    # --- CONFIG ---
    OFFICE_CASH_ACCOUNT_ID = 6
    BANK_ACCOUNT_IDS = [537, 558, 8024, 8806]

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for w in self:
            if w.date_from and w.date_to and w.date_from > w.date_to:
                raise Warning('Date From must be <= Date To')

    # -------- Helpers --------
    def _sql_state_clause(self):
        if self.target_move == 'posted':
            return " AND m.state = %s ", ['posted']
        return "", []

    def _opening_balance(self, account_id):
        clause, params = self._sql_state_clause()
        self.env.cr.execute("""
            SELECT COALESCE(SUM(l.debit - l.credit), 0.0)
              FROM account_move_line l
              JOIN account_move m ON (m.id = l.move_id)
             WHERE l.account_id = %s
               AND l.company_id = %s
               AND l.date < %s
        """ + clause, [account_id, self.company_id.id, self.date_from] + params)
        return float(self.env.cr.fetchone()[0] or 0.0)

    def _period_totals(self, account_id):
        clause, params = self._sql_state_clause()
        self.env.cr.execute("""
            SELECT COALESCE(SUM(l.debit), 0.0), COALESCE(SUM(l.credit), 0.0)
              FROM account_move_line l
              JOIN account_move m ON (m.id = l.move_id)
             WHERE l.account_id = %s
               AND l.company_id = %s
               AND l.date >= %s
               AND l.date <= %s
        """ + clause, [account_id, self.company_id.id, self.date_from, self.date_to] + params)
        debit, credit = self.env.cr.fetchone()
        return float(debit or 0.0), float(credit or 0.0)

    def _lines(self, account_id, extra_domain=None):
        domain = [
            ('account_id', '=', account_id),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.target_move == 'posted':
            domain += [('move_id.state', '=', 'posted')]
        if extra_domain:
            domain += extra_domain

        return self.env['account.move.line'].search(domain, order='date, move_id, id')

    def _account_basic_info(self, account_id):
        acc = self.env['account.account'].browse(account_id)
        return {'id': acc.id, 'code': acc.code, 'name': acc.name}

    def _build_cash_portion(self):
        cash_id = self.OFFICE_CASH_ACCOUNT_ID
        cash_info = self._account_basic_info(cash_id)

        opening = self._opening_balance(cash_id)
        debit_sum, credit_sum = self._period_totals(cash_id)
        closing = opening + (debit_sum - credit_sum)

        credit_line_ids = self._lines(cash_id, extra_domain=[('credit', '>', 0.0)]).ids

        return {
            'account': cash_info,
            'opening': opening,
            'total_debit': debit_sum,
            'credit_line_ids': credit_line_ids,
            'total_credit': credit_sum,
            'closing': closing,
        }

    def _build_bank_portion(self):
        banks = self.env['account.account'].browse(list(self.BANK_ACCOUNT_IDS))
        bank_sections = []
        for b in banks:
            opening = self._opening_balance(b.id)
            debit_sum, credit_sum = self._period_totals(b.id)
            closing = opening + (debit_sum - credit_sum)
            line_ids = self._lines(b.id).ids

            bank_sections.append({
                'account': {'id': b.id, 'code': b.code, 'name': b.name},
                'opening': opening,
                'debit': debit_sum,
                'credit': credit_sum,
                'closing': closing,
                'line_ids': line_ids,
                'has_txn': bool(line_ids),
            })
        return bank_sections

    def get_report_data(self):
        self.ensure_one()
        return {
            'company': {'id': self.company_id.id, 'name': self.company_id.name},
            'date_from': self.date_from,
            'date_to': self.date_to,
            'target_move': self.target_move,
            'cash_portion': self._build_cash_portion(),
            'bank_sections': self._build_bank_portion(),
        }

    @api.multi
    def action_print_report(self):
        """PDF"""
        self.ensure_one()
        data = self.get_report_data()
        # This uses the PDF report action
        return self.env['report'].get_action(self, 'cash_bank.cash_bank_book_qweb', data=data)

    @api.multi
    def action_preview_report(self):
        """HTML Preview (no download) - Odoo 8 compatible"""
        self.ensure_one()
        data = self.get_report_data()

        # IMPORTANT: Odoo 8 uses /report/html/<report_name>/<docids>?options=...
        options = urllib.quote(json.dumps(data))
        url = "/report/html/cash_bank.cash_bank_book_qweb/%s?options=%s" % (self.id, options)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',   # 'new' if you want new tab
        }
