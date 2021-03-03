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



class HrEmployee(models.Model):
	_inherit = 'hr.employee'

	location_id = fields.Many2one('work.location',string='Work Address')
	emp_no = fields.Integer('Employee Number',required=True)
	bu_id = fields.Many2one('asset.bu.br.division',string='BU / BR / Division',required=True)

class StockLocation(models.Model):
	_inherit = 'stock.location'
	
	def _get_default_name(self):
		resp_obj = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
		return resp_obj
	
	emp_id = fields.Many2one('hr.employee',string='PIC Name',default=_get_default_name)

class WorkLocation(models.Model):
	_name = 'work.location'

	name = fields.Char('Name')