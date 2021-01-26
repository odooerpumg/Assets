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

from ast import literal_eval
from datetime import date
from itertools import groupby
from operator import itemgetter
import time

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class AssetRequest(models.Model):
	_name = 'asset.request'
	
	def _get_default_name(self):
		resp_obj = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
		return resp_obj
	
	request_date = fields.Date('Request Date', default=fields.Date.today)
	request_id = fields.Many2one('hr.employee',string='PIC Name',default=_get_default_name)
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
#		self.create_transfer()

	def create_transfer(self):
		res = self.env['stock.picking'].search([('id', '=', 12)])
# 		datas = { 
#                  'picking_type_id':5,
#                  'location_id':8,
#                  'location_dest_id':8 ,
# 				 'move_line_ids_without_package':res.move_line_ids_without_package.ids       
#                     }  
# 		
# 		stock_id = self.env['stock.picking'].create(datas)
		res.action_confirm()
		res.action_assign()
		res.button_validate()



class StockPicking(models.Model):
	_inherit = 'stock.picking'
	
	def button_validate(self):
		self.ensure_one()
		if not self.move_lines and not self.move_line_ids:
			raise UserError(_('Please add some items to move.'))

		ctx = dict(self.env.context)
		ctx.pop('default_immediate_transfer', None)
		self = self.with_context(ctx)
		self.message_subscribe([self.env.user.partner_id.id])
		picking_type = self.picking_type_id
		precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
		no_reserved_quantities = all(float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in self.move_line_ids)
		if no_reserved_quantities and no_quantities_done:
			raise UserError(_('You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))
		
		if picking_type.use_create_lots or picking_type.use_existing_lots:
			lines_to_check = self.move_line_ids
			if not no_quantities_done:
				lines_to_check = lines_to_check.filtered(
				    lambda line: float_compare(line.qty_done, 0,
				                               precision_rounding=line.product_uom_id.rounding)
				)
			for line in lines_to_check:
				product = line.product_id
				if product and product.tracking != 'none':
					if not line.lot_name and not line.lot_id:
						raise UserError(_('You need to supply a Lot/Serial number for product %s.') % product.display_name)
					
		sms_confirmation = self._check_sms_confirmation_popup()
		if sms_confirmation:
			return sms_confirmation

#         if no_quantities_done:
		view = self.env.ref('stock.view_immediate_transfer')
		wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
		return {
	        'name': _('Immediate Transfer?'),
	        'type': 'ir.actions.act_window',
	        'view_mode': 'form',
	        'res_model': 'stock.immediate.transfer',
	        'views': [(view.id, 'form')],
	        'view_id': view.id,
	        'target': 'new',
	        'res_id': wiz.id,
	        'context': self.env.context,
	    }
		if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
			view = self.env.ref('stock.view_overprocessed_transfer')
			wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
			return {
		        'type': 'ir.actions.act_window',
		        'view_mode': 'form',
		        'res_model': 'stock.overprocessed.transfer',
		        'views': [(view.id, 'form')],
		        'view_id': view.id,
		        'target': 'new',
		        'res_id': wiz.id,
		        'context': self.env.context,
		    }
		
		# Check backorder should check for other barcodes
		if self._check_backorder():
			return self.action_generate_backorder_wizard()
		self.action_done()
		return
		

	
	
	



class AssetRequestLine(models.Model):
	_name = 'asset.request.line'

	asset_id = fields.Many2one('asset.request', string='Asset ID')
	name = fields.Char('Asset Name')
	qr_code = fields.Char('QR Code',groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
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
