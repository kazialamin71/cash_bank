# -*- coding: utf-8 -*-
from openerp import models, api

class ReportCashBankBook(models.AbstractModel):
    _name = 'report.cash_bank.cash_bank_book_qweb'

    @api.multi
    def render_html(self, data=None):
        data = data or {}
        env = self.env

        cash = data.get('cash_portion', {}) or {}
        cash_credit_ids = cash.get('credit_line_ids', []) or []
        cash['credit_lines'] = env['account.move.line'].browse(cash_credit_ids)

        bank_sections = data.get('bank_sections', []) or []
        for sec in bank_sections:
            ids_ = sec.get('line_ids', []) or []
            sec['lines'] = env['account.move.line'].browse(ids_)

        docargs = {
            'doc_ids': self._ids,
            'doc_model': 'cash.bank.book.wizard',
            'docs': env['cash.bank.book.wizard'].browse(self._ids),
            'data': data,
        }
        return env['report'].render('cash_bank.cash_bank_book_qweb', docargs)
