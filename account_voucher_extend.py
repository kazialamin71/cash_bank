# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import api
from datetime import datetime

class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    def _compute_disburse_priority(self, cr, uid, ids, name, args, context=None):
        context = context or {}
        today = fields.date.context_today(self, cr, uid, context=context)
        res = {}
        for v in self.browse(cr, uid, ids, context=context):
            res[v.id] = 1 if (v.cheque_disburse_date == today) else 0
        return res

    _columns = {
        'cheque_number': fields.char('Cheque Number', required=True),
        'cheque_issue_date': fields.date('Issue Date',required=True),
        'cheque_disburse_date': fields.date('Disburse Date',required=True),

        # used only for sorting
        'disburse_priority': fields.function(
            _compute_disburse_priority,
            type='integer',
            string='Disburse Priority',
            store=True,   # IMPORTANT: we will update via cron too
        ),
    }

    @api.multi
    def action_print_bank_debit_voucher(self):
        self.ensure_one()
        if not self.move_id:
            raise Warning("Please post/validate the voucher first (no journal entry found).")
        return self.env['report'].get_action(
            self.move_id, 'cash_bank.report_bank_debit_voucher'
        )

    @api.model
    def cron_refresh_disburse_priority(self):
        # force recompute daily by writing cheque_disburse_date to itself
        ids = self.search([])
        for v in self.browse(ids):
            v.write({'cheque_disburse_date': v.cheque_disburse_date})
        return True
