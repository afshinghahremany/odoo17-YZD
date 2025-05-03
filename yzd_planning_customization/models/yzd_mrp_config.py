from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # فقط برای تولید
    yzd_production_capacity = fields.Float(
        string='ظرفیت کل خط تولید',
        config_parameter='yzd.production_capacity',
        help='ظرفیت کل خط تولید (تن در ماه)',
        groups='mrp.group_mrp_user',
    )

    # فقط برای برنامه‌ریزی
    yzd_planning_allow_past_start = fields.Boolean(
        string='اجازه برنامه‌ریزی برای تاریخ گذشته',
        config_parameter='yzd.planning_allow_past_start',
        help='اگر فعال باشد، کاربر می‌تواند برای تاریخ گذشته برنامه‌ریزی کند.',
        groups='planning.group_planning_manager',
    )