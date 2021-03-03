from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError
import os
import re
import xlrd
from xlrd import open_workbook
from datetime import datetime,timedelta
import base64
import logging
from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

header_fields = ['badge_id', 'date', 'amount', 'reason']


class DataImportAttendance(models.Model):
    _name = "dataimport.product"
    _description = 'Product Import'
    _order = 'id DESC'

    name = fields.Char('Description')
    import_date = fields.Date('Import Date', default=fields.Date.today)
    import_fname = fields.Char('Filename', size=128)
    import_file = fields.Binary('File', required=True)
    note = fields.Text('Log')
    
    
    
    def get_default_image(self, image):
        image_value = tools.image_resize_image_big(open(image, 'rb').read().encode('base64').strip())
        # image_value = image_value.replace('==', '')
        return image_value
     
    @api.onchange('import_fname')
    def onchange_import_fname(self):
        if self.import_fname:
            # Check Heading
            p, ext = os.path.splitext(self.import_fname)
            if ext:
                ext_name = ext.split('.')[1]
                if ext_name.lower() not in ('xls', 'xlsx'):
                    raise UserError(_("Please import EXCEL file!"))
            else:
                raise UserError(_("Please import EXCEL file!"))
 
    def import_data(self):
        product_obj = self.env['product.template']
        log_msg = ''
        lines = base64.decodestring(self.import_file)
        wb = xlrd.open_workbook(file_contents=lines)
        sheet = wb.sheet_by_index(0)
        badge_idx = date_idx = amount_idx = reason_idx = None
        deduction_data = []
        success_rows = []
 
        if sheet.nrows < 2:
            raise UserError(_("There is no line to import"))
 
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            if rowx > 1:
                value = {}
#                 if row[0].value:
                bu_br = row[0].value
                deaprt_id = row[1].value
                location = row[2].value
                asset_name = row[3].value
                brand = row[4].value
                p_type = row[5].value
                user_name = row[6].value
                qr = row[7].value
#                 image_medium = row[8].value
#                 if image_medium:
#                     image = self.get_default_image(image_medium)
                bu_obj = self.env['umg.bu']
                bu_br_obj = bu_obj.search([('name', '=', bu_br)])
                if not bu_br_obj:
                    bu = bu_br_obj.create({'name':bu_br})
                    value['bu_br_id'] = bu.id
                else:
                    value['bu_br_id'] = bu_br_obj.id
                
                depart_ob = self.env['umg.department']
                depart_obj = depart_ob.search([('name', '=', deaprt_id)])
                if not depart_obj:
                    deaprt_id = depart_ob.create({'name':deaprt_id})
                    value['department_id'] = deaprt_id.id
                else:
                    value['department_id'] = depart_obj.id
                
                
                product_ob = self.env['product.location']
                product_objs = product_ob.search([('name', '=', location)])
                if not product_objs:
                    prod_id = product_ob.create({'name':location})
                    value['product_location_id'] = prod_id.id
                else:
                    value['product_location_id'] = product_objs.id    
                    
                brand_ob = self.env['product.brand']
                brand_objs = brand_ob.search([('name', '=', brand)])
                if not brand_objs:
                    ban_id = brand_ob.create({'name':brand})
                    value['brand_id'] = ban_id.id
                else:
                    value['brand_id'] = brand_objs.id
                
                pt_ob = self.env['product.type']
                pt_obj = pt_ob.search([('name', '=', p_type)])
                if not pt_obj:
                    pt_id = pt_ob.create({'name':p_type})
                    value['type_id'] = pt_id.id
                else:
                    value['type_id'] = pt_obj.id
                
                
                resp_ob = self.env['res.partner']
                resp_obj = resp_ob.search([('name', '=', user_name)], limit=1)
                if not resp_obj:
                    resp_id = resp_ob.create({'name':user_name})
                    value['user_type'] = resp_id.id
                else:
                    value['user_type'] = resp_obj.id
                
                
                value['name'] = asset_name
                value['barcode'] = qr
#                 value['image_1920'] = image
#                 else:
#                     log_msg += '\nRow No %s :: Empty Badge ID ' % rowx
#                     continue
                value['row_no'] = rowx
                value['type'] = 'product'
                deduction_data.append(value)
 
        for ded in deduction_data:
            row_no = ded['row_no']
            ded.pop('row_no', None)
            product_obj.create(ded)
            success_rows.append(row_no)
  
        if success_rows:
            success_msg = 'Row Numbers - %s are successfully imported!\n' % str(success_rows)
            log_msg = success_msg + log_msg
  
        self.write({'note': log_msg})