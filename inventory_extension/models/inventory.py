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

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bu_br = fields.Char('Bu/Br')
    department_id = fields.Char('Department Name')
    location_id = fields.Char('Location')
    brand_id = fields.Many2one('product.brand',string='Brand')
    type_id = fields.Text('Type')
    user_type = fields.Char('User Name/Type')

class ProductType(models.Model):
    _name = 'product.type'

    name = fields.Char('Product Type')


class ProductBrand(models.Model):
    _name = 'product.brand'

    name = fields.Char('Brand Name')

class ProductLocation(models.Model):
    _name = 'product.location'

    name = fields.Char('Product Location')