from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResUser(models.Model):
    _inherit = 'res.users'

    @api.model
    def has_group_users(self, group_ext_id):
        """
        查询有某个res_group的所有用户
        """
        assert group_ext_id and '.' in group_ext_id, "External ID '%s' must be fully qualified" % group_ext_id
        module, ext_id = group_ext_id.split('.')
        self._cr.execute("""
            SELECT
                uid 
            FROM
                res_groups_users_rel 
            WHERE
                gid IN ( SELECT res_id FROM ir_model_data WHERE MODULE = %s AND NAME = %s ) 
                AND uid NOT IN (
            SELECT
                uid 
            FROM
                res_groups_users_rel 
            WHERE
                gid IN ( SELECT res_id FROM ir_model_data WHERE MODULE = 'base' AND NAME = 'group_system' ))
        """,
                         (module, ext_id))
        query_datas = self._cr.fetchall()
        return [query_data[0] for query_data in query_datas]