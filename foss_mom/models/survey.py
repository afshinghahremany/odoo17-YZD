from odoo import models, fields, api

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    calendar_event_id = fields.Many2one('calendar.event', string='جلسه مرتبط')
    survey_type = fields.Selection(selection_add=[('live_meeting', 'جلسه زنده')], 
        ondelete={'live_meeting': 'set default'})

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    calendar_event_id = fields.Many2one('calendar.event', string='جلسه',
        related='survey_id.calendar_event_id', store=True)
