from odoo import models, fields, api, _
from odoo.tools.misc import format_date

class Meeting(models.Model):
    _inherit = 'calendar.event'

    survey_id = fields.Many2one('survey.survey', string='نظر سنجی جلسه', 
        help='نظر سنجی ایجاد شده برای این جلسه')
    survey_user_input_ids = fields.One2many('survey.user_input', 'calendar_event_id', 
        string='پاسخ‌های نظر سنجی')
    survey_required = fields.Boolean('نظر سنجی اجباری', default=False,
        help='در صورت فعال بودن، شرکت‌کنندگان باید نظر سنجی را تکمیل کنند')

    def action_create_survey(self):
        self.ensure_one()
        # ایجاد یک نظر سنجی جدید
        survey = self.env['survey.survey'].create({
            'title': f'نظر سنجی {self.name}',
            'survey_type': 'live_meeting',
            'is_time_limited': True,
            'time_limit': self.duration,
            'is_attempts_limited': True,
            'attempts_limit': 1,
            'calendar_event_id': self.id,
            'users_login_required': True,
            'questions_layout': 'one_page',
            'is_time_limited': False,
        })
        
        # اضافه کردن حاضرین جلسه به فالورهای نظرسنجی
        existing_followers = survey.message_follower_ids.mapped('partner_id')
        for partner in self.partner_ids:
            if partner not in existing_followers:
                self.env['mail.followers'].create({
                    'partner_id': partner.id,
                    'res_model': 'survey.survey',
                    'res_id': survey.id,
                })
        
        # اتصال نظر سنجی به جلسه
        self.write({
            'survey_id': survey.id,
            'survey_required': True
        })

        # ارسال نوتفیکیشن به حاضرین جلسه
        survey_url = f'/survey/start/{survey.access_token}'
        message = _("""
            <p>نظرسنجی جلسه <strong>%s</strong> ایجاد شد.</p>
            <p>لطفاً با کلیک روی لینک زیر در نظرسنجی شرکت کنید:</p>
            <p><a href="%s" class="btn btn-primary">ورود به نظرسنجی</a></p>
            <p>این نظرسنجی تا پایان جلسه (%s) فعال خواهد بود.</p>
        """) % (
            self.name,
            survey_url,
            format_date(self.env, self.stop)
        )
        
        # ارسال پیام به کانال نظرسنجی
        survey.message_post(
            body=message,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            partner_ids=self.partner_ids.ids
        )

        # بازگشت اکشن برای باز کردن فرم نظر سنجی
        return {
            'type': 'ir.actions.act_window',
            'name': _('ایجاد نظر سنجی'),
            'res_model': 'survey.survey',
            'view_mode': 'form',
            'res_id': survey.id,
            'target': 'current',
        }

    def action_view_survey(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('نظر سنجی'),
            'res_model': 'survey.survey',
            'view_mode': 'form',
            'res_id': self.survey_id.id,
            'target': 'current',
        }

    def action_create_live_meeting(self):
        self.ensure_one()
        # ایجاد جلسه زنده و نظرسنجی
        survey = self.env['survey.survey'].create({
            'title': f'نظر سنجی {self.name}',
            'survey_type': 'live_meeting',
            'is_time_limited': True,
            'time_limit': self.duration,
            'is_attempts_limited': True,
            'attempts_limit': 1,
            'calendar_event_id': self.id,
        })
        self.write({
            'survey_id': survey.id,
            'survey_required': True
        })
        # اضافه کردن فالورها
        existing_followers = survey.message_follower_ids.mapped('partner_id')
        for partner in self.partner_ids:
            if partner not in existing_followers:
                self.env['mail.followers'].create({
                    'partner_id': partner.id,
                    'res_model': 'survey.survey',
                    'res_id': survey.id,
                })
        # ارسال پیام نوتیفیکیشن
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        survey_url = f"{base_url}/survey/start/{survey.access_token}"
        message = _("""
            <p>نظرسنجی جلسه <strong>%s</strong> ایجاد شد.</p>
            <p>لطفاً با کلیک روی لینک زیر در نظرسنجی شرکت کنید:</p>
            <p><a href="%s" class="btn btn-primary">ورود به نظرسنجی</a></p>
            <p>این نظرسنجی تا پایان جلسه (%s) فعال خواهد بود.</p>
        """) % (
            self.name,
            survey_url,
            fields.Date.to_string(self.stop)
        )
        survey.message_post(
            body=message,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            partner_ids=self.partner_ids.ids
        )
        # بازگشت اکشن
        return {
            'type': 'ir.actions.act_window',
            'name': _('ایجاد جلسه زنده و نظرسنجی'),
            'res_model': 'survey.survey',
            'view_mode': 'form',
            'res_id': survey.id,
            'target': 'current',
        }
