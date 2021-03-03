from odoo import fields, models, api
# from odoo.osv import orm
import xlrd
import codecs
from xlrd import open_workbook
from odoo.tools.translate import _
from datetime import datetime
import base64
import logging
from passlib.tests.backports import skip
from odoo.exceptions import ValidationError
from odoo import tools
import base64
from PIL import Image
_logger = logging.getLogger(__name__)

# header_fields = ['name_related', 'categ_id','department','job','work_location','work_phone','phone',
# 'work_email','gender','doj', 'trial_date_end','birthday','father_name','nrc_number', 'nrc_code', 'nrc_desc', 'nrc_no','marital','graduate_status',
# 'address','wage', 'trial_date_end','education','other_quali','tax_father_name','tax_spouse',
# 'working_experience','working_experience_year','working_experience_company','no_of_child','spouse_name','branch_location']

header_fields = ['category_code','parent_id','name']




header_indexes = {}

class EmployeeImport(models.Model):
    _name = 'data_import.category'

    name = fields.Char(string='Description')
    import_date = fields.Date(string='Import Date', readonly=True, default=fields.Date.today())
    import_fname = fields.Char(string='Filename')
    import_file = fields.Binary(string='File', required=True)
    note = fields.Text(string='Log')
    company_id = fields.Many2one('res.company',  string='Company', required=False)
    state = fields.Selection([('draft', 'Draft'),('completed', 'Completed'),('error', 'Error')], string='States', default='draft')
    
    err_log = ''

    def _check_file_ext(self):
        for import_file in self.browse(self.ids):
            if '.xls' or '.xlsx' in import_file.import_fname:return True
            else: return False
        return True
    
    _constraints = [(_check_file_ext, "Please import EXCEL file!", ['import_fname'])]
    
    # ## Load excel data file
    def get_excel_datas(self, sheets):
        result = []
        for s in sheets:
            # # header row
            headers = []
            header_row = 0
            for hcol in range(0, s.ncols):
                headers.append(s.cell(header_row, hcol).value)
                            
            result.append(headers)
            
            # # value rows
            for row in range(header_row + 1, s.nrows):
                values = []
                for col in range(0, s.ncols):
                    values.append(s.cell(row, col).value)
                result.append(values)
        return result
    
    # ## Check excel row headers with header_fields and define header indexes for database fields
    def get_headers(self, line):
        if line[0].strip().lower() not in header_fields:
                    raise orm.except_orm(_('Error :'), _("Error while processing the header line %s.\
                     \n\nPlease check your Excel separator as well as the column header fields") % line)
        else:
            # ## set header_fields to header_index with value -1
            for header in header_fields:
                header_indexes[header] = -1  
                     
            col_count = 0
            for ind in range(len(line)):
                if line[ind] == '':
                    col_count = ind
                    break
                elif ind == len(line) - 1:
                    col_count = ind + 1
                    break
            
            for i in range(col_count):                
                header = line[i].strip().lower()
                if header not in header_fields:
                    self.err_log += '\n' + _("Invalid Excel File, Header Field '%s' is not supported !") % header
                else:
                    header_indexes[header] = i
                                
            for header in header_fields:
                if header_indexes[header] < 0:                    
                    self.err_log += '\n' + _("Invalid Excel file, Header '%s' is missing !") % header
    
    #### Fill excel row data into list to import to database
    def get_line_data(self, line):
        result = {}
        for header in header_fields:                        
            result[header] = line[header_indexes[header]]

    #thurein soe, 20180730,
    def floatHourToTime(self, fh):
        h, r = divmod(fh, 1)
        m, r = divmod(r*60, 1)
        return (
            int(h),
            int(m),
            int(r*60),
        )

    def get_default_image(self, image):
        image_value = tools.image_resize_image_big(open(image, 'rb').read().encode('base64').strip())
        # print image_value, '--------------------------------- image value'
        # image_value = image_value.replace('==', '')
        return image_value

    ######### Read data and import to database ##########        
    def import_data(self):
        product_category_obj = self.env['product.category']


        company_id = self.company_id.id
        import_file = self.import_file                
        
        header_line = True
        lines = base64.decodestring(import_file)
        wb = open_workbook(file_contents=lines)
        excel_rows = self.get_excel_datas(wb.sheets())        
        value = {}
        all_data = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        parent_dep = image = 0
        
        for line in excel_rows:
            if not line or line and line[0] and line[0] in ['', '#']:
                continue
            
            if header_line:
                self.get_headers(line)
                header_line = False                           
            elif line and line[0] and line[0] not in ['#', '']:
                import_vals = {}
                # ## Fill excel row data into list to import to database
                for header in header_fields:
                    #print "----------------------header---------------------"
                    #print header
                    #print line
                    
                    #print "..........header error..........",line[header_indexes[header]]
                    import_vals[header] = line[header_indexes[header]]
                
                all_data.append(import_vals)
       
        # if self.err_log <> '':
        #     import_id = self.ids[0]
        #     err = self.err_log
        #     #self.write(self.ids[0], {'note': ''})
        #     self.write({'note': err,'state': 'error'})
        # else:
            for data in all_data:
                print ('----------------------------------Employee data are now importing-------------------------------------------')
                print ('excel row => ' + str(all_data.index(data) + 2))
                #print 'data ' + str(data)

                
                sub_categ = None
                
                ##### to hold value for database
                value = {}
                
                
                name = str(data['name'])
                category_code = int(data['category_code'])
                parent_id = data['parent_id']

                
                if parent_id:
                    parent_ids = product_category_obj.search([('category_code', '=', parent_id)])
                    if not parent_ids:
                        parent_value = {'name': name,'category_code': parent_id}
                        parent_idds = product_category_obj.create(parent_value).id
                    else:
                        parent_idds = parent_ids[0].id
                else:
                    parent_idds = None

                if parent_idds == None:
                    sub_categ = False
                else:
                    sub_categ = True
                

                if category_code:
                    categ_ids = product_category_obj.search([('category_code','=',category_code)])
                    # print "business_unit>>>>>>>",business_id.id
                    if not categ_ids:
                        categ_values = {
                            'name': name,
                            'category_code': category_code,
                            'parent_id': parent_idds,
                            'sub_categ': sub_categ
                            
                        }
                        
                        categ_id = product_category_obj.create(categ_values)
                        categ_id = categ_id.id
                        created_count += 1
                        print (".................Creating.............................")
                    else:
                        categ_values = {
                            'name': name,
                            'category_code': category_code,
                            'parent_id': parent_idds,
                            'sub_categ': sub_categ
                        }
                        
                        print ("UPDATING <><><><><><>><>")
                        categ_ids.write(categ_values)
                        categ_id = categ_ids[0].id
                        updated_count += 1

                    print ("category's id ", categ_id)

                else:
                    skipped_count += 1


                percent = ((created_count + updated_count)*100)/len(all_data)
                print ('(' + str(percent) + '%)' + str(updated_count + created_count) + ' records of total ' + str(len(all_data)) + ' completed')
            
            message = 'Import Success at ' + str(datetime.strptime(datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                      '%Y-%m-%d %H:%M:%S'))+ '\n' + str(len(all_data))+' records imported' +'\
                      \n' + str(created_count) + ' created\n' + str(updated_count) + ' updated' 
                      
            self.write({'state': 'completed','note': message})



