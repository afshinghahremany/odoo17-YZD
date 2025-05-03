# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MailActivity(models.Model):

    _inherit = 'mail.activity'

    stage_id = fields.Many2one('mail.activity.stage', string='阶段')
    color = fields.Integer('颜色序号', default=0)

class ActivityStage(models.Model):
    _name = 'mail.activity.stage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '活动阶段'

    name = fields.Char('阶段')