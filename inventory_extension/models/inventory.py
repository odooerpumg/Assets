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


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    request_id = fields.Many2one('asset.request',string='Stock Request')
    returned_id = fields.Many2one('return.asset',string='Stock Return')
    contact_id = fields.Many2one('hr.employee',string='Contacts')



class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    def _get_default_false(self):
        
        res=False
        return res

    bu_br_id = fields.Many2one('umg.bu','Bu/Br/DIV')
    department_id = fields.Many2one('umg.department','Department Name')
    product_location_id = fields.Many2one('product.location',string='Product Location')
    brand_id = fields.Many2one('product.brand',string='Brand')
    type_id = fields.Many2one('product.type','Type')
    user_type = fields.Many2one('res.partner','User Name')
    barcode = fields.Char('QR Code', related='product_variant_ids.barcode', readonly=False)
    qty = fields.Integer('Qty')
    is_damage = fields.Boolean('Is Damage ?',default=_get_default_false)
    

class ProductType(models.Model):
    _name = 'product.type'
    
    name = fields.Char('Product Type')

class ProductLocation(models.Model):
    _name = 'product.location'

    name = fields.Char('Product Location')

    
class Department(models.Model):
    _name = 'umg.department'

    name = fields.Char('Department Name')
    
    
class BUBR(models.Model):
    _name = 'umg.bu'

    name = fields.Char('BU/BR/DIV')    


class ProductBrand(models.Model):
    _name = 'product.brand'

    name = fields.Char('Brand Name')

