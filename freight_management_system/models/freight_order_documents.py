from datetime import datetime, date, timedelta
import re
from xml.dom import ValidationErr
from odoo import api, fields, models, _


class FreightOrderDocument(models.Model):
    """Create a new module for retrieving document files, allowing users
     to input details about the documents."""
    _name = 'freight.order.documents'
    _description = 'Freight Order Documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Document Number', readonly=True, copy=False,default='New',
                       help="Enter Document Number")
    document_type_readonly = fields.Boolean(compute='_compute_document_type_readonly', store=True)
    document_type = fields.Selection([('Bill of Lading', 'بارنامه'),
                                      ('Weight Certificate','قبض باسکول'),
                                      ('Commercial Invoice', 'فاکتور خرید'),
                                      ('Packing List', 'لیست بسته‌بندی'),
                                      ('Certificate of Origin','گواهی مبدأ'),
                                      ('Customs Declaration','اظهارنامه گمرکی'),    
                                      ('Import/Export License','مجوز واردات یا صادرات'),
                                      ('Insurance Certificate','گواهی بیمه'),
                                      ('Letter of Credit (L/C)','اعتبار اسنادی'),
                                      ('Bank Draft','حواله بانکی'),
                                      ('Delivery Order','دستور تحویل'),
                                      ('Inspection Certificate','گواهی بازرسی'),
                                      ('Other','سایر'),
                                      ],
                                     string='Checklist Type', required=1,
                                     help="Select checklist type for document")
    description = fields.Text(string='Description', copy=False,
                              help="Description for Employee Document")
    expiry_date = fields.Date(string='Expiry Date', copy=False,
                              help="Choose Expiry Date for Employee Document")
    freight_order_id = fields.Many2one('freight.order', copy=False, string="Freight Order",
                                  help="Choose Freight Order for Freight Order Document")
    doc_attachment_ids = fields.Many2many('ir.attachment',
                                          'doc_attach_ids',
                                          'doc_id', 'attach_id3',
                                          string="Attachment",
                                          help='You can attach the copy'
                                               'of your document',
                                          copy=False)
    issue_date = fields.Date(string='Issue Date',
                             default=fields.Date.context_today, copy=False,
                             help="Choose Issue Date for Employee Document")
    bill_of_lading_id = fields.One2many('freight.order.document.billoflading', 'freight_order_document_id', 
                                       string='مشخصات بارنامه', copy=False,
                                       help="Bill of Lading Details")
    baskol_id = fields.One2many('freight.order.document.baskol', 'freight_order_document_id', 
                               string='قبض باسکول', copy=False,
                               help="Baskol Details")
    
    @api.depends('bill_of_lading_id', 'baskol_id')
    def _compute_document_type_readonly(self):
        for rec in self:
            rec.document_type_readonly = bool(rec.bill_of_lading_id or rec.baskol_id)
    
    def mail_reminder(self):
        """Function for scheduling emails to send reminders
        about document expiry dates."""
        for doc in self.search([]):
            if doc.expiry_date:
                if (datetime.now() + timedelta(days=1)).date() >= (
                        doc.expiry_date - timedelta(days=7)):
                    mail_content = ("  Hello  " + str(
                        doc.employee_id.name) + ",<br>Your Document " + str(
                        doc.name) + "is going to expire on " + \
                                    str(doc.expiry_date) + ". Please renew it "
                                                           "before expiry date")
                    main_content = {
                        'subject': _('Document-%s Expired On %s') % (
                            str(doc.name), str(doc.expiry_date)),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': doc.employee_id.work_email,
                    }
                    self.env['mail.mail'].create(main_content).send()

    @api.onchange('expiry_date')
    def check_expr_date(self):
        """Function to obtain a validation error for expired documents."""
        if self.expiry_date and self.expiry_date < date.today():
            return {
                'warning': {
                    'title': _('Document Expired.'),
                    'message': _("Your Document Is Already Expired.")
                }
            }

    @api.constrains('document_type')
    def _check_document_type_change(self):
        for rec in self:
            if rec.bill_of_lading_id and rec.document_type != 'Bill of Lading':
                raise ValidationError(_('به دلیل وجود اطلاعات بارنامه، امکان تغییر نوع سند وجود ندارد.'))
            if rec.baskol_id and rec.document_type != 'Weight Certificate':
                raise ValidationError(_('به دلیل وجود اطلاعات قبض باسکول، امکان تغییر نوع سند وجود ندارد.'))

    @api.onchange('document_type')
    def _onchange_document_type(self):
        if self.document_type:
            if self.bill_of_lading_id and self.document_type != 'Bill of Lading':
                return {
                    'warning': {
                        'title': _('تغییر نوع سند غیرمجاز'),
                        'message': _('به دلیل وجود اطلاعات بارنامه، امکان تغییر نوع سند وجود ندارد.')
                    }
                }
            elif self.baskol_id and self.document_type != 'Weight Certificate':
                return {
                    'warning': {
                        'title': _('تغییر نوع سند غیرمجاز'),
                        'message': _('به دلیل وجود اطلاعات قبض باسکول، امکان تغییر نوع سند وجود ندارد.')
                    }
                }

    @api.model_create_multi
    def create(self, vals_list):
        """Create Sequence for multiple records"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('freight.order.document.sequence') or 'New'
        return super(FreightOrderDocument, self).create(vals_list)
    


class FreightOrderDocumentBillofLading(models.Model):
    """Create a new module for retrieving document files, allowing users
     to input details about the documents."""
    _name = 'freight.order.document.billoflading'
    _description = 'Freight Order Documents Bill of Lading'
    freight_order_document_id = fields.Many2one('freight.order.documents', copy=False, string="Freight Order Document",
                                  help="Choose Freight Order Document for Freight Order Document Bill of Lading")
    name = fields.Char(string='Document Number', required=True, copy=False,default='New',
                       help="Enter Document Number")
    date_of_issue = fields.Date(string='Date of Issue', default=fields.Date.context_today, copy=False,
                                help="Choose Date of Issue for Employee Document")
    reference_number = fields.Char(string='Reference Number', required=True, copy=False,
                                help="Enter Reference Number")
    driver_name = fields.Char(string='Driver Name', required=True, copy=False,
                                help="Enter Driver Name")
    driver_phone = fields.Char(string='Driver Phone', required=True, copy=False,
                                help="Enter Driver Phone")
    driver_national_code = fields.Char(string='Driver National Code', required=True, copy=False,
                                help="Enter Driver National Code")
    vehicle_number_type = fields.Selection([('iran', 'ایران'), ('intl', 'بین الملی')], string='نوع پلاک', required=True, copy=False,
                                help="Choose Vehicle Number Type for Freight Order Document Bill of Lading", default='iran')
    vehicle_number = fields.Char(string='پلاک خودرو', required=True, copy=False,
                                help="Enter Vehicle Number")
    arrival_date = fields.Date(string='پیش بینی ورود', default=fields.Date.context_today, copy=False,
                                help="Choose Arrival Date for Freight Order Document Bill of Lading")
    delivery_company_id = fields.Many2one('res.partner', string='شرکت حمل کننده', required=True, copy=False,
                                help="Choose Delivery Company for Freight Order Document Bill of Lading")
    
    # @api.constrains('vehicle_number')
    # def _check_vehicle_number_format(self):
    #     iran_plate_pattern = r'^\d{2}[آ-ی]\d{3} ?ایران\d{2}$'
    #     intl_plate_pattern = r'^[A-Z0-9\- ]{5,20}$'  # ساده‌شده برای شماره‌های بین‌المللی

    #     for rec in self:
    #         if rec.vehicle_number:
    #             if not (re.match(iran_plate_pattern, rec.vehicle_number) or re.match(intl_plate_pattern, rec.vehicle_number)):
    #                 raise ValidationErr("فرمت شماره پلاک وارد شده صحیح نیست. نمونه ایرانی: 12الف345 ایران88")

class FreightOrderDocumentBaskol(models.Model):
    _name = 'freight.order.document.baskol'
    _description = 'Freight Order Documents Baskol'
    freight_order_document_id = fields.Many2one('freight.order.documents', copy=False, string="Freight Order Document",
                                  help="Choose Freight Order Document for Freight Order Document Baskol")

    name = fields.Char(string='Document Number', required=True, copy=False,default='New',
                       help="Enter Document Number")
    date_of_issue = fields.Date(string='Date of Issue', default=fields.Date.context_today, copy=False,
                                help="Choose Date of Issue for Employee Document")
    empty_weight = fields.Float(string='Empty Weight', required=True, copy=False,
                                help="Enter Empty Weight")
    full_weight = fields.Float(string='Full Weight', required=True, copy=False,
                                help="Enter Full Weight")
    net_weight = fields.Float(string='Net Weight', required=True, copy=False,
                                help="Enter Net Weight" ,compute='_compute_net_weight')
    
    @api.depends('empty_weight', 'full_weight')
    def _compute_net_weight(self):
        for rec in self:
            if rec.full_weight and rec.empty_weight:
                rec.net_weight = abs(rec.full_weight - rec.empty_weight)
            else:
                rec.net_weight = 0.0
    
   
    
    
    
    
    
    
