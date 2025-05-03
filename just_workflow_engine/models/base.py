# -*- coding: utf-8 -*-
##############################################################################
import logging

from lxml import etree

from odoo import api, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.models import BaseModel as BM
from odoo.addons.base.models.ir_ui_view import Model as VM
import datetime
import re, json

_logger = logging.getLogger(__name__)

## odoo.workflow.workitem.workflow_expr_eval_expr
def workflow_trans_condition_expr_eval(self, lines):
    result = False
    #_logger.info('condition_expr_eval %s' % lines)
    for line in lines.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line == 'True':
            result = True
        elif line == 'False':
            result = False
        else:
            result = eval(line)
    return result

default_create = BM.create

def default_create_new(self, vals):
    id = default_create(self, vals)
    ctx = self.env.context
    todo_id = ctx.get('workflow_todo_id')
    if todo_id:
        todo = self.env['todo.activity'].browse(int(todo_id))
        if todo.real_model == self._name:
            todo.write({'real_id':id})
    return id
        
default_write = BM.write

def default_write_new(self, vals):
    res = default_write(self, vals)
    event_model = self.env['ir.config_parameter'].sudo().get_param('event_model')
    if len(self) == 1 and event_model and self._name in event_model:
        ctx = self.env.context.copy()
        todos = self.env['todo.activity'].search([('real_model','=',self._name),('real_id','=',self.id),('todo_state','!=','complete')])
        for todo in todos:
            trans = self.env['workflow.trans'].browse(todo.trans_id)
            if self.workflow_trans_condition_expr_eval(trans.node_from.task_condition):
                todo.done()
                order = self.env[todo.res_model].browse(todo.res_id)
                ctx.update({'trans_id':trans.id})
                order.with_context(ctx).workflow_action(trans.node_from.name + _(' event trigged.'))
                
    return res
    
# Set default state
default_get_old = BM.default_get

@api.model
def default_get_new(self, fields_list):
    res = default_get_old(self, fields_list)
    if 'x_workflow_state' in fields_list:
        res.update({'x_workflow_state': self.env['workflow.base'].get_default_state(self._name)})
    return res

def workflow_button_action(self):
    ctx = self.env.context.copy()
    t_id = int(self.env.context.get('trans_id'))
    trans = self.env['workflow.trans'].browse(t_id)
    node = trans.node_from
    # _logger.info('workflow_button_action %s' % self.env.context)
    ctx.update({'workflow_active_id': self.id, 'workflow_active_ids': self.ids})
    if node.trans_type == 'note':
        logtype = 1
        if not ctx.get('workflow_todo_id') :
            logtype = 0
        elif node.audit_type == 'notify':
            logtype = 0
        elif self.env['log.workflow.trans'].search([('res_id', '=', self.id), ('write_uid', '=', self.env.uid),('todo','=',int(ctx.get('workflow_todo_id')))], limit=1):
            logtype = 0
        elif ctx.get('workflow_todo_id') and self.env.uid not in self.env['todo.activity'].browse(int(ctx.get('workflow_todo_id'))).user_ids.ids:
            logtype = 0
        ctx.update({'default_logType': logtype})
        return {
            'name': _(u'Flow Approve'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'wizard.workflow.message',
            'type': 'ir.actions.act_window',
            # 'view_id': False,
            'target': 'new',
            'context': ctx,
        }
    elif node.trans_type == 'task':
        ctx.update({'workflow_task_model': node.task_model,'x_workflow_vstate':node.id})
        if node.context:
            ctx.update(eval(node.context))
        self.env['todo.activity'].add_todo(
                 self,
                 datetime.date.today(),
                 node.compute_approve_ids() or [self.env.uid],
                 node.name,
                 _('Todo Task'),
                 node.model_view_id,
                 'stage_workflow',
                 node.menu_id,
                 node.task_model,
                 eval(node.real_id),
                 context = ctx,
                 note_type = 'many',
                 trans_id = trans.id,
                 node_id = node.id)
    elif node.trans_type == 'time':
        self.env['todo.activity'].add_todo(
                 self,
                 datetime.date.today(),
                 node.compute_approve_ids() or [self.env.uid],
                 node.name,
                 _('Event Detection'),
                 node.model_view_id,
                 'stage_state',
                 node.menu_id,
                 node.task_model,
                 eval(node.real_id),
                 context = ctx,
                 note_type = 'many',
                 trans_id = trans.id,
                 node_id = node.id)
    else:
        return self.with_context(ctx).workflow_action()

def workflow_buttons_action(self):
    ctx = self.env.context.copy()
    # _logger.info('workflow_button_action %s' % self.env.context)
    t_id = int(self.env.context.get('buttons_id'))
    button = self.env['workflow.buttons'].browse(t_id)
    ctx.update({'workflow_active_id': self.id, 'workflow_active_ids': self.ids})
    return button.with_context(ctx).run()

def workflow_action(self, message=''):
    ctx = self.env.context.copy()
    t_id = int(self.env.context.get('trans_id'))
    trans = self.env['workflow.trans'].browse(t_id)
    node = trans.node_to

    condition_ok = workflow_trans_condition_expr_eval(self, trans.condition)
    #_logger.info('>>>>>>%s: %s, %s', trans.condition, condition_ok, self.env.context)

    if not condition_ok:
        _logger.info('condition false:%s', trans.condition)
        return True

    # # check repeat trans
    # if not trans.is_backward:
    #     if self.env['log.workflow.trans'].search([('res_id', '=', self.id), ('trans_id', '=', t_id),('create_uid','=',self.env.user.id)], limit=1):
    #         raise UserError(_('The transfer had finish'))
    #         return False;

    # check note
    # if trans.need_note and not self.x_workflow_note:
    #    _logger.warning(_('The transfer can not empty note'))

    # check  can be trans
    can_trans = trans.node_from.check_trans_in(self.id)
    
    if can_trans:
        # done and log
        if (message == ''):
            message = (trans.node_from.name + ' -> ' + trans.name) if trans.name else trans.node_from.name
        log = trans.node_from.make_log(self.name, self.id, message, ctx.get('workflow_todo_id'),trans.id)

        self.write({'x_workflow_state': str(node.id)})
        self.write({'x_workflow_approve_user': False})
        trans_approve_users = []
        if node.is_approve and not node.is_stop:
            trans_approve_users = node.compute_approve_ids()
            self.write({'x_workflow_approve_user': ','.join(node.user_ids.mapped('name'))})

        # action
        if trans.is_backward:
            node.backward_cancel_logs(self.id)
        if trans.name and trans.action_type:
            trans.with_context(ctx).run()

        # 2:calendar event
        if node.event_need:
            node.make_event(self.name, trans_approve_users, self)

        # post todo task when is note type
        if node.trans_type == "note":
            ctx.update({'workflow_active_id': self.id, 'workflow_active_ids': self.ids, 'x_workflow_vstate':node.id})
            self.env['todo.activity'].add_todo(
                 self,
                 datetime.date.today(),
                 node.compute_approve_ids() or [self.env.uid],
                 node.name,
                 _('Review comments'),
                 node.workflow_id.view_id,
                 'stage_approve',
                 self.env.ref("just_workflow_engine.menu_workflow_root", False),
                 self._name,
                 self.id,
                 context = ctx,
                 note_type = 'many' if node.audit_type != 'counter_sign' else 'one',
                 trans_id = trans.id,
                 node_id = node.id)
        else:
            for auto_t in node.out_trans:
                self.with_context(trans_id=auto_t.id).workflow_button_action()

        # notify
        if node.audit_type == 'notify':
           odoobot = self.env.ref("base.partner_root")
           self.message_post(
                body = node.notify if node.notify else '%s %s -> %s' % (_("Approve has done, "), trans.name, node.name),
                message_type='comment', 
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
                author_id=odoobot.id,
                partner_ids=node.compute_approve_ids(),
            )

def workflow_button_show_log(self):
    ctx = self.env.context.copy()
    ctx.update({'workflow_active_id': self.id, 'workflow_active_ids': self.ids, 'default_logType': 0})
    return {
        'name': _(u'Workflow approval log'),
        'view_type': 'form',
        "view_mode": 'form',
        'res_model': 'wizard.workflow.message',
        'type': 'ir.actions.act_window',
        # 'view_id': False,
        'target': 'new',
        'context': ctx,
    }

def workflow_button_link(self):
    self.ensure_one()
    workflow_id = self.env.context.get('workflow_id')
    view_id = self.env.ref("just_workflow_engine.view_workflow_base_diagram").id
    action = {
        'name': _('Diagram'),
        'type': 'ir.actions.act_window',
        'view_mode': 'diagram_plus',
        'view_id': view_id,
        'target': 'current',
        'res_model': 'workflow.base',
        'res_id': workflow_id,
        'context': {'workflow_id': workflow_id, 'res_model': self._name, 'res_id': self.id,'form_view_initial_mode': 'view'},
    }
    return action

def workflow_button_reset(self, workflow_id=False):
    logs = self.env['log.workflow.trans'].search([('res_id', '=', self[0].id), ('model', '=', self._name)])
    logs.write({'active': False})
    workflow_id = workflow_id or self.env.context.get('workflow_id')
    state = self.env['workflow.base'].browse(workflow_id).default_state
    self.write({'x_workflow_state': state})
    return True

def workflow_button_stop(self, workflow_id=False):
    #logs = self.env['log.workflow.trans'].search([('res_id', '=', self[0].id), ('model', '=', self._name)])
    #logs.write({'active': False})
    workflow_id = workflow_id or self.env.context.get('workflow_id')
    state = self.env['workflow.base'].browse(workflow_id).stop_state
    self.write({'x_workflow_state': state})
    return True

old_fields_view_get = VM.get_view

def update_fields_view(self, view_id, res):
    """
        Updates fields attributes.
        :param view_type: Type of view now rendering.
        :param res: View resource data.
        :return: Updated view resource.
    """
    # Objects
    workflow_obj = self.env['workflow.base']
    user_obj = self.env['res.users']
    # Variables
    model = self._name
    uid = self._uid
    workflow_rec = workflow_obj.search([('model_id', '=', model)])
    arch = etree.fromstring(res['arch'])
    is_workflow_from = arch.xpath("//field[@name='x_workflow_state']")
    if not workflow_rec.isActive or is_workflow_from is None:
        return res

    # Helper Functions
    def _get_external_id(group):
        arr = []
        ext_ids = group._get_external_ids()
        for ext_id in ext_ids:
            arr.append(ext_ids[ext_id][0])
        return arr

    # Read fields of view
    for field in res['models'][res['model']]:
        # Get Fields Instance
        field_inst = arch.xpath("//field[@name='%s']" % str(field))
        field_inst = field_inst[0] if field_inst else False
        # Scope Variables
        readonly_arr = []
        required_arr = []
        invisible_arr = []

        # Loop all nodes
        for node in workflow_rec.node_ids:
            # Loop Other Nodes
            for field_attrs in node.field_ids:
                # Record all states for each attribute
                if field_inst is not False and field_attrs.name.name == field_inst.attrib['name']:
                    flag_show = False
                    # Check Users & Groups
                    if field_attrs.user_ids:
                        user_rec = user_obj.browse(uid)
                        if user_rec in field_attrs.user_ids:
                            flag_show = True
                    if field_attrs.group_ids:
                        has_group = False
                        user_rec = user_obj.browse(uid)
                        ext_ids = _get_external_id(field_attrs.group_ids)
                        for ext_id in ext_ids:
                            has_group = user_rec.has_group(ext_id)
                            if has_group:                          
                                flag_show = True
                                        
                    if field_attrs.readonly and flag_show:
                        readonly_arr.append(str(node.id))
                    if field_attrs.required and flag_show:
                        required_arr.append(str(node.id))
                    if field_attrs.invisible and flag_show:
                        invisible_arr.append(str(node.id))

        # Construct XML attribute
        if readonly_arr != [] and field_inst is not False:
            field_inst.set('readonly', "x_workflow_vstate in " + str(readonly_arr))
        if required_arr != [] and field_inst is not False:
            field_inst.set('required', "x_workflow_vstate in " + str(required_arr))
        if invisible_arr != [] and field_inst is not False:
            field_inst.set('invisible', "x_workflow_vstate in " + str(invisible_arr))
    
    res['arch'] = etree.tostring(arch, encoding="utf-8")
    return res

@api.model
def new_fields_view_get(self, view_id=None, view_type='form', **options):
    '''<button   user_ids="1,2,3" '''
    res = old_fields_view_get(self, view_id=view_id, view_type=view_type, **options)
    if view_type == 'form' and res['models'][res['model']] and 'x_workflow_vstate' in res['models'][res['model']]:
        res = self.update_fields_view(view_id, res)
        view = etree.fromstring(res['arch'])

        realtime_users = []
        ctx = self.env.context
        for tag in view.xpath("//button[@user_ids]"):
            if ctx.get('trans_id'):
                todos = self.env['todo.activity'].search(['&',('trans_id','=',ctx.get('trans_id')),('res_id','=',ctx.get('active_id'))])
                realtime_users = todos.mapped('user_ids').ids
            users_str = tag.get('user_ids')
            user_ids = [int(i) for i in users_str.split(',')] + realtime_users if len(realtime_users) > 0 else []
            if self._uid not in user_ids and self._uid not in [SUPERUSER_ID,2]:
                tag.getparent().remove(tag)
        res['arch'] = etree.tostring(view)
    return res


BM.write = default_write_new
BM.create = default_create_new
BM.default_get = default_get_new
BM.workflow_button_action = workflow_button_action
BM.workflow_action = workflow_action
BM.workflow_button_show_log = workflow_button_show_log
BM.workflow_button_reset = workflow_button_reset
BM.workflow_button_stop = workflow_button_stop
VM.get_view = new_fields_view_get
BM.update_fields_view = update_fields_view
BM.workflow_button_link = workflow_button_link
BM.workflow_buttons_action = workflow_buttons_action
BM.workflow_trans_condition_expr_eval = workflow_trans_condition_expr_eval
######################################################################


##############################
