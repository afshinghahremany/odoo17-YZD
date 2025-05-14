from odoo import models, fields, api, _

class ProductionPlanningReturnWizard(models.TransientModel):
    _name = 'production.planning.return.wizard'
    _description = 'Return Reason Wizard'

    reason = fields.Text(string='علت بازگشت', required=True)

    def action_confirm(self):
        planning = self.env['production.planning'].browse(self.env.context.get('active_id'))
        if planning:
            planning.message_post(body=_("علت بازگشت: %s" % self.reason))
            planning.state = 'draft'
