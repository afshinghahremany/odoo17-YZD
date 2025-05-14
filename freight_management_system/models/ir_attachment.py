from odoo import fields, models

class IrAttachment(models.Model):
    """Inherit the 'ir_attachment' model to retrieve attached documents."""
    _inherit = 'ir.attachment'

    doc_attach_ids = fields.Many2many('freight.order.documents',
                                      'doc_attachment_ids',
                                      'attach_id3',
                                      'doc_id',
                                      string="Attachment", invisible=1,
                                      help="Choose Freight Order Document for"
                                           " Attachment")