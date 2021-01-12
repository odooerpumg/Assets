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

class WorkLocation(models.Model):
	_name = 'work.location'

	name = fields.Char('Name')