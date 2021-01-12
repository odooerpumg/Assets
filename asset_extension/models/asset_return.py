import calendar
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from requests.auth import HTTPBasicAuth
import hashlib
import json
import requests
import locale

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero
from odoo.osv import expression

class AssetReturn(models.Model):
    _name = 'return.asset'

    return_date = fields.Date('Return Date', default=fields.Date.today)
    return_emp_id = fields.Many2one('hr.employee',string='PIC Name')
    return_person_id = fields.Many2one('hr.employee',string='Return by Employee')
    email = fields.Char(string='PIC Email')
    emp_no = fields.Char(string='Employee Number')
    ph_no = fields.Char('Phone Number')
    department_id = fields.Many2one('hr.department', string='Department Name')
    bu_id = fields.Many2one('asset.bu.br.division',string='BU / BR / Division Name')
    line_ids = fields.One2many('asset.return.line', 'return_id', string='Asset Return Line')
    state = fields.Selection([
        ('draft', 'Request'),
        ('request', 'Requested'),
        ('manager_approve','Manager Approved'),
        ('ga_approve', 'GA Approved'),
        ('ga_manager_approve', 'GA Manager Approved'),
        ('it_approve', 'IT Approved'),
        ('it_manager_approve','IT Manager Approved'),
        ('approve', 'Management Approved'),
        ('cancel', 'Cancelled'),
        ('refuse', 'Refused'),
        ],
        'Status',default="draft")
    
    is_it = fields.Boolean('Is IT ?',default=False)
    is_ga = fields.Boolean('Is GA ?',default=False)
    ga_it = fields.Selection([
        ('ga', 'GA Asset'),
        ('it', 'IT Asset'),
        ],
        'Choose GA or IT Asset')
    
    @api.onchange('return_emp_id')
    def _onchange_emp(self):
        if self.return_emp_id:
            self.email = self.return_emp_id.work_email
            self.emp_no = self.return_emp_id.emp_no
#             self.ph_no = self.return_emp_id.
            
    
    def draft(self):
        self.write({'state': 'draft'})
    
    def cancel(self):
        self.write({'state': 'cancel'})
    
    def refuse(self):
        self.write({'state': 'refuse'})
    def request(self):
        self.write({'state': 'request'})

    def manager_approve(self):
        self.write({'state': 'manager_approve','is_ga': True})
        if self.ga_it == 'it':
            self.is_it = True

    def ga_approve(self):
        self.write({'state': 'ga_approve'})

    def ga_manager_approve(self):
        if self.ga_it == 'it':
            self.is_it = True
        self.write({'state': 'ga_manager_approve'})

    def it_approve(self):
        self.is_it = False
        self.write({'state': 'it_approve'})

    def it_manager_approve(self):
        self.write({'state': 'it_manager_approve'})

    
    
class AssetReturnLine(models.Model):
    _name = 'asset.return.line'

    return_id = fields.Many2one('return.asset', string='Asset ID')
    name = fields.Char('Asset Name')
    type_id = fields.Many2one('product.template', string='Type')
    qty = fields.Integer('Quantity',default=1)
    current_value = fields.Float('Current Value')
    qr_code = fields.Char("QR Code")
    conditions = fields.Selection([
                                  ('damage', 'Damage'),
                                  ('good', 'Good Condition'),
                                  ],groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
    reason = fields.Selection([
                                  ('life_end', 'Life End'),
                                  ('user_fault', 'User Fault'),
                                  ],groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
#     reason = fields.Text('Reason')
    remark = fields.Text('Remark')   
    @api.onchange('type_id')
    def _onchange_use_alias(self):
        if self.type_id:
            self.name = self.type_id.name
            self.current_value = self.type_id.list_price
            self.qr_code = self.type_id.barcode
            
            
        