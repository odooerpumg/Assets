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
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _get_default_name(self):
        resp_obj = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        return resp_obj
    
    name = fields.Char('Name')
    return_date = fields.Date('Return Date', default=fields.Date.today)
    return_emp_id = fields.Many2one('hr.employee',string='PIC Name' ,default=_get_default_name)
    return_person_id = fields.Char(string='Return by Employee')
    return_by_emp_id = fields.Char(string='Return by Employee ID')
    email = fields.Char(related='return_emp_id.work_email',string='PIC Email')
    emp_no = fields.Integer(related='return_emp_id.emp_no',string='Employee ID')
    ph_no = fields.Char('Phone Number')
    department_id = fields.Many2one('hr.department', string='Department Name')
    bu_id = fields.Many2one('asset.bu.br.division',string='BU / BR / Division Name',default=lambda self: self.env.user.bu_id)
    location_id = fields.Many2one('work.location',string='Office Location')
    line_ids = fields.One2many('asset.return.line', 'return_id', string='Asset Return Line')
    stock_location_dest_id = fields.Many2one('stock.location',string='Main Stock Location',groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
    from_location_id = fields.Many2one('stock.location',string='BU Stock Location',groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
    transfer_state = fields.Char('Product Transfer State')
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
        'Status',default="draft",tracking=True)
    
    is_it = fields.Boolean('Is IT ?',default=False)
    is_ga = fields.Boolean('Is GA ?',default=False)
    ga_it = fields.Selection([
        ('ga', 'GA Asset'),
        ('it', 'IT Asset'),
        ],
        'Choose GA or IT Asset')
    
    @api.model
    def create(self, vals):
        res = super(AssetReturn, self).create(vals)
        name = 'RT'+str(res.id)
        res.name = name
        return res
    
    
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
        self.create_transfer()

    def it_approve(self):
        self.is_it = False
        self.write({'state': 'it_approve'})

    def it_manager_approve(self):
        self.write({'state': 'it_manager_approve'})
        self.create_transfer()
    
    
    def create_transfer(self):
        datas = { 
                'name':'RT'+str(self.id),
                'contact_id':self.return_emp_id.id,
                 'picking_type_id':10,
                 'location_id':self.from_location_id.id,
                 'location_dest_id':self.stock_location_dest_id.id ,
                 'returned_id':self.id
                    }  
        stock_id = self.env['stock.picking'].create(datas)
        res = self.env['asset.return.line'].search([('return_id', '=', self.id)])
        for line in res:
            product = self.env['product.product'].search([('barcode', '=', line.qr_code)])
            data = { 
                    'name':product.name,
                    'product_id':product.id,
                    'product_uom_qty':line.qty,
                    'picking_id':stock_id.id,
                    'product_uom':product.product_tmpl_id.uom_id.id,
                    'location_id':self.from_location_id.id,
                    'location_dest_id':self.stock_location_dest_id.id,
                    
                     
                        }  
            stock_id.env['stock.move'].create(data)
        stock_id.action_confirm()
        stock_id.action_assign()
        stock_id.button_validate()    
        if stock_id.state=='assigned':
            self.transfer_state = 'Ready'


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def button_validate(self):
        if self.request_id:
            res = self.env['return.asset'].search([('id', '=', self.returned_id.id)])
            res.update({
                     'transfer_state':'Done'
                    })
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
        if no_quantities_done:
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
        
   
    
class AssetReturnLine(models.Model):
    _name = 'asset.return.line'

    return_id = fields.Many2one('return.asset', string='Asset ID')
    name = fields.Char('Asset Name')
    type_id = fields.Many2one('product.template', string='Type')
    qty = fields.Integer('Quantity')
    current_value = fields.Float('Current Value')
    qr_code = fields.Char("QR Code")
    product_condi = fields.Selection([
                                  ('damage', 'Damage'),
                                  ('good', 'Good Condition'),
                                  ],groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
    reason = fields.Selection([
                                  ('life_end', 'Life End'),
                                  ('user_fault', 'User Fault'),
                                  ],groups="asset_extension.group_ga_pic,asset_extension.group_ga_manager,asset_extension.group_it_pic,asset_extension.group_it_manager,asset_extension.group_management,asset_extension.group_admin")
#     reason = fields.Text('Reason')
    g_f = fields.Boolean(default=False)
    is_qrcode = fields.Boolean(string='Have Not QR Code',default=False)
    remark = fields.Text('Remark')   
    @api.onchange('product_condi')
    def _onchange_product_condi(self):
        if self.product_condi == 'good':
            self.g_f = True
        else:
            self.g_f= False    
            
            
        