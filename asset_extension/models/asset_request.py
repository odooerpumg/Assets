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

class AssetRequest(models.Model):
	_name = 'asset.request'

	request_date = fields.Date('Request Date', default=fields.Date.today)
	request_id = fields.Many2one('hr.employee',string='PIC Name')
	request_person_id = fields.Many2one('hr.employee',string='Request by Employee')
	email = fields.Char(related='request_id.work_email',string='Request Person Email')
	emp_no = fields.Integer(related='request_id.emp_no',string='Employee Number')
	ph_no = fields.Char('Phone Number')
	department_id = fields.Many2one('hr.department', related='request_id.department_id', string='Department Name')
	bu_id = fields.Many2one('asset.bu.br.division',string='BU / BR / Division Name')
	asset_type_id = fields.Many2one('asset.types',string='Asset Types')
	location_id = fields.Many2one('work.location',string='Office Location')
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
		('refuse', 'Refuse'),
		],
		'Status',default="draft")
	is_it = fields.Boolean('Is IT ?',default=False)
	is_ga = fields.Boolean('Is GA ?',default=False)
	new_old = fields.Selection([
		('new', 'New Asset'),
		('old', 'Old Asset'),
		],
		'Choose New or Old')
	line_ids = fields.One2many('asset.request.line', 'asset_id', string='Asset Request Line')
	model_id = fields.Many2one('asset.model', string='Model Name')
	other_info = fields.Text('Other Information')
	asset_condition = fields.Char('Asset Condition')
	prev_bu_id = fields.Many2one('asset.bu.br.division', string='Previous BU/BR/Division')
	ga_it = fields.Selection([
		('ga', 'GA Asset'),
		('it', 'IT Asset'),
		],
		'Choose GA or IT Asset')
# 	is_management = fields.Boolean('Is Managemenet',default=False)

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
# 		if self.new_old == 'new':
# 			self.is_management = True
		self.write({'state': 'ga_manager_approve'})

	def it_approve(self):
		self.is_it = False
		self.write({'state': 'it_approve'})

	def it_manager_approve(self):
		self.write({'state': 'it_manager_approve'})

# 	def approve(self):
# 		self.is_management = False
# 		self.write({'state': 'approve'})

class AssetRequestLine(models.Model):
	_name = 'asset.request.line'

	asset_id = fields.Many2one('asset.request', string='Asset ID')
	name = fields.Char('Asset Name')
	qty = fields.Integer('Quantity')
	unit_price = fields.Float('Unit Price')
	remark = fields.Text('Remark')
	
class AssetBusinessUnit(models.Model):
	_name = 'asset.bu.br.division'

	name = fields.Char('Name')

class AssetTypes(models.Model):
	_name = 'asset.types'

	name = fields.Char('Name')

class AssetModel(models.Model):
	_name = 'asset.model'

	name = fields.Char('Name')