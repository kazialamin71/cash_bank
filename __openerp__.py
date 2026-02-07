# -*- coding: utf-8 -*-
{
    'name': 'Cash Flow & Bank Book (Odoo 8)',
    'version': '8.0.1.0.0',
    'author': 'Custom',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/cash_bank_book_view.xml',
        'report/cash_bank_book_template.xml',
        'report/bank_debit_voucher.xml',
    ],
    'installable': True,
}
