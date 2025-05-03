# -*- coding: utf-8 -*-
##############################################################################
import logging
from datetime import datetime, date, time, timedelta

from lxml.etree import XML, tostring

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .xml_templdate import *
from lxml import etree
from odoo.models import BaseModel

_logger = logging.getLogger(__name__)

PYTHON_CODE_TEMP = """# Available locals:
#  - time, date, datetime, timedelta: Python libraries.
#  - env: Odoo Environement.
#  - model: Model of the record on which the action is triggered.
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - user, Current user object.
#  - workflow: Workflow engine.
#  - syslog : syslog(message), function to log debug information to Odoo logging file or console.
#  - warning: warning(message), Warning Exception to use with raise.
# To return an action, assign: action = {...}


"""
class workflow_base(models.Model):
    _name = 'workflow.base'
    _description = 'Workflow Base'
    _def_workflow_state_name = 'x_workflow_state'
    _def_workflow_vstate_name = 'x_workflow_vstate'
    _def_workflow_note_name = 'x_workflow_note'
    _def_workflow_approve_user = 'x_workflow_approve_user'

    @api.depends('node_ids')
    def _compute_default_state(self):
        def _get_start_state(nodes):
            if not nodes: return None
            star_id = nodes[0].id
            for n in nodes:
                if n.is_start:
                    star_id = n.id
                    break
            return str(star_id)

        def _get_stop_state(nodes):
            if not nodes: return None
            stop_id = nodes[0].id
            for n in nodes:
                if n.is_stop:
                    stop_id = n.id
                    break
            return str(stop_id)

        nodes = self.node_ids
        show_nodes = filter(lambda x: x.show_state, nodes)
        no_rest_nodes = filter(lambda x: x.no_reset, nodes)

        self.show_states = ','.join([str(x.id) for x in show_nodes])
        self.default_state = _get_start_state(nodes)
        self.stop_state = _get_stop_state(nodes)
        self.no_reset_states = ','.join(["'%s'" % x.id for x in no_rest_nodes])
        self.no_reset_groups = ["'%s'" % x.id for x in no_rest_nodes]

    @api.model
    def _default_reset_group(self):
        return self.env['ir.model.data'].sudo()._xmlid_to_res_id('base.group_system')

    name = fields.Char('Name', required=True)

    model_id = fields.Many2one('ir.model', 'Module ID', ondelete="set null",
        help="Select a model that you want to create the Workflow. If workflow has actived, can not change the model unless you stop the workflow.")
    model = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    model_view_id = fields.Many2one('ir.ui.view', 'Model  View',
                                    help="The form view of the model that want to extend Workflow button on it",
                                    ondelete="set null")
    model_tree_view_id = fields.Many2one('ir.ui.view', 'list view',  ondelete="set null")
    view_id = fields.Many2one('ir.ui.view', 'Add View', readonly=True,
                              help="The auto created Workflow extend view, show Workflow button, state, logs..", )
    tree_view_id = fields.Many2one('ir.ui.view', 'tree view', readonly=True)
    widget_view_id = fields.Many2one('ir.ui.view', 'widget form', readonly=True)

    node_ids = fields.One2many('workflow.node', 'workflow_id', 'Node', help='Nodes')
    trans_ids = fields.One2many('workflow.trans', 'workflow_id', 'Transfer', help='Transfers,')
    isActive = fields.Boolean('Active', default=False)
    field_id = fields.Many2one('ir.model.fields', 'Field Workflow-State', help="The Workflow State field",
                               readonly=True)
    field_id1 = fields.Many2one('ir.model.fields', 'Field Workflow-vState', help="The Workflow vState field",
                               readonly=True)
    field_id2 = fields.Many2one('ir.model.fields', 'Field Workflow-Approve', help="next approve",
                                readonly=True)
    tracking = fields.Integer('Tracking Wkf state', default=1)

    allow_reset = fields.Boolean("Allow to reset the Workflow", default=True,
                                 help="If True, This Workflow allow to reset draft")
    reset_group = fields.Many2one('res.groups', "Group Reset", default=_default_reset_group, required=True,
                                  help="Workflow Reset Button Groups, default Admin")
    no_reset_states = fields.Char(compute='_compute_default_state', string='No Reset States',
                                  help='Which state u can to reset the Workflow')
    no_reset_groups = fields.Char(compute='_compute_default_state', string='No Reset Groups')

    default_state = fields.Char(compute='_compute_default_state', string="Default Workflow State value", store=False,
                                help='The default Workflow state, It is come from the star node')
    show_states = fields.Char(compute='_compute_default_state', string="Default  States to display", store=False,
                              help='Which status can show the state widget, It is set by node')
    stop_state = fields.Char(compute='_compute_default_state', string="stop States", store=False,
                              help='The cancle Workflow state, It is come from the stop node')
    buttons_ids = fields.One2many('workflow.buttons', 'workflow_id', 'buttons')
    
    is_replace = fields.Boolean('Replace')
    diagram = fields.Text('workflow diagram', default=""" <?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:omgdi="http://www.omg.org/spec/DD/20100524/DI" xmlns:omgdc="http://www.omg.org/spec/DD/20100524/DC" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="sid-38422fae-e03e-43a3-bef4-bd33b32041b2" targetNamespace="http://bpmn.io/bpmn" exporter="bpmn-js (https://demo.bpmn.io)" exporterVersion="9.0.3">
  <process id="Process_1" isExecutable="false">
  </process>
  <bpmndi:BPMNDiagram id="BpmnDiagram_1">
    <bpmndi:BPMNPlane id="BpmnPlane_1" bpmnElement="Process_1">
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions> """)
    
    @api.constrains('model_id')
    def check_uniq(self):
        for one in self:
            if self.search_count([('model_id', '=', one.model_id.id)]) > 1:
                raise UserError('workflow must be unique fer model')

    @api.model
    def get_default_state(self, model):
        return self.search([('model', '=', model)]).default_state

    @api.model
    def get_stop_state(self, model):
        return self.search([('model', '=', model)]).stop_state

    def define_workflow(self):
        self.ensure_one()
        view_id = self.env.ref("just_workflow_engine.view_workflow_base_diagram").id
        return {
                'name': self.name +  _('Diagram'),
                'type': 'ir.actions.act_window',
                'view_mode': 'diagram_plus',
                'view_id': view_id,
                'target': 'current',
                'res_model': 'workflow.base',
                'res_id': self.id,
                "breadcrumbs": True,
        }

    @api.model
    def subflow(self, nodeid):
        view_id = self.env.ref("just_workflow_engine.view_workflow_base_diagram").id
        node = self.env['workflow.node'].browse(nodeid)
        subflow = self.env['workflow.base'].search([('model', '=', node.task_model)])
        return {
                'name': node.name + _('Subflow'),
                'type': 'ir.actions.act_window',
                'view_mode': 'diagram_plus',
                'view_id': view_id,
                'views': [(view_id, 'diagram_plus')],
                'target': 'current',
                'res_model':'workflow.base',
                'res_id': subflow.id,
        }

    def sync2ref_model(self):
        self.ensure_one()
        self._check()
        self.make_field()
        self.make_view()
        #self.make_widget_view()
        self.make_tree_view()
        self.write({'isActive': True})
        self.event_model()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _check(self):
        if not any([n.is_start for n in self.node_ids]):
            raise UserError('Please check the nodes setting, not found a start node')
        if not self.show_states:
            raise UserError('Please check the nodes setting, At least one show state is required')

    def make_workflow_contain(self):
        workflow_contain = XML(workflow_contain_template)
        workflow_contain.append(self.make_btm_contain())
        #workflow_contain.append(
        #    XML(workflow_field_approve_user % (self.field_id2.name, self.field_id2.name, self.field_id2.name)))
        workflow_contain.append(XML(wfk_field_state_template % (self.field_id.name, self.show_states)))
        workflow_contain.append(XML(wfk_field_vstate_template % (self.field_id1.name)))
        return workflow_contain

    def make_btm_contain(self):
        btn_contain = XML(bton_contain_template)
        trans_buttons = {r for r in self.node_ids 
                         if (r.trans_type not in ['task','auto'] or r.is_start) and len(r.out_trans.ids) > 0 }
        for t in trans_buttons:
            className = t.trans_type in ['note','auto'] and 'oe_highlight' or  'oe_highlight oe_disabled'
            btnName = t.trans_type in ['task','time'] and 'wait ' or ''
            btn = XML(btn_template % {'btn_str': _(btnName) +  t.name, 'trans_id': t.out_trans.ids[0], 'vis_state': t.id,
                'className':className,'workflow_model_name': self.model, 'model_id': self.model_id.id})
            
            # 2024-01-27 add audit_type
            # if t.group_ids:
            #     btn.set('groups', t.xml_groups)
            user_ids = []
            user_ids = t.compute_approve_ids()
            if user_ids:
                user_ids_str = ','.join([str(x) for x in user_ids])
                btn.set('user_ids', user_ids_str)
            #if not t.auto:
            btn_contain.append(btn)

        for button in self.buttons_ids:
            btn = XML(
                button2_template % {'btn_str': button.name, 'buttons_id': button.id, 'vis_state': button.belong_node.id,
                                    'workflow_model_name': self.model, 'model_id': self.model_id.id})
            if button.group_ids:
                btn.set('groups', button.xml_groups)
            if button.user_ids:
                user_ids_str = ','.join([str(x.id) for x in button.user_ids])
                btn.set('user_ids', user_ids_str)
            btn_contain.append(btn)

        btn_contain.append(XML(btn_show_log_template % {'btn_str': _('Flowlogs'), 'btn_grp': 'base.group_user'}))
        # btn_contain.append(XML(btn_workflow_reset_template % {'btn_str': _('Turnback'), 'btn_grp': 'base.group_system', 'btn_ctx': self.id, 'no_reset_states': self.no_reset_states}))
        btn_contain.append(XML(btn_workflow_link_template % {'btn_str': _('Diagram'),'btn_grp': 'base.group_user', 'btn_ctx': self.id}))
        return btn_contain
    
    def remove_special_characters(self, string):
        special_characters = "!@#$%^&*()_+{}[]|\:;'<>?,./\""
        return [char for char in string if char not in special_characters]

    def make_view(self):
        self.ensure_one()
        view_obj = self.env['ir.ui.view'].sudo()
        have_header = '<header>' in self.model_view_id.arch
        arch = XML(arch_template_no_header)
        if have_header:
            arch = XML(arch_template_header)
        if have_header and self.is_replace:
            arch = XML(arch_template_header_replace)

        workflow_contain = self.make_workflow_contain()

        arch.insert(0, workflow_contain)

        form_view_data = {
            'name': '%s.WKF.form.view' % self.model,
            'type': 'form',
            'model': self.model,
            'inherit_id': self.model_view_id.id,
            'mode': 'extension',
            'arch': tostring(arch, encoding='unicode'),
            'priority': 99999,
        }

        # update or create view
        view = self.view_id
        if not view:
            view = view_obj.create(form_view_data)
            self.write({'view_id': view.id})
        else:
            view.write(form_view_data)
        return True

    def make_widget_view(self):
        self.ensure_one()
        view_obj = self.env['ir.ui.view'].sudo()
        arch = XML(widget_template)
        form_view_data = {
            'name': '%s.widget.WKF.form.view' % self.model,
            'type': 'form',
            'model': self.model,
            # 'inherit_id': self.model_view_id.id,
            'mode': 'primary',
            'arch': tostring(arch, encoding='unicode'),
            'priority': 99999,
        }
        view = self.widget_view_id
        if not view:
            view = view_obj.create(form_view_data)
            self.write({'widget_view_id': view.id})
        else:
            view.write(form_view_data)
        return True

    def make_tree_view(self):
        self.ensure_one()
        view_obj = self.env['ir.ui.view']
        if self.model_tree_view_id:
            arch_tree = XML(tree_template_inhert)
            arch_tree.insert(0, XML('<field name="x_workflow_state" string="workflow step"/>'))
            tree_view_data = {
                'name': '%s.WKF.tree.view' % self.model,
                'type': 'tree',
                'model': self.model,
                'inherit_id': self.model_tree_view_id.id,
                'mode': 'extension',
                'arch': tostring(arch_tree),
                'priority': 99999,
            }
            tree_view = self.tree_view_id
            if not tree_view:
                tree_view = view_obj.create(tree_view_data)
                self.write({'tree_view_id': tree_view.id})
            else:
                tree_view.write(tree_view_data)
        return True

    def make_field(self):
        self.ensure_one()
        fd_obj = self.env['ir.model.fields'].sudo()
        fd_id = fd_obj.search([('name', '=', self._def_workflow_state_name), ('model_id', '=', self.model_id.id)])
        fd_id1 = fd_obj.search([('name', '=', self._def_workflow_vstate_name), ('model_id', '=', self.model_id.id)])
        fd_id2 = fd_obj.search([('name', '=', self._def_workflow_approve_user), ('model_id', '=', self.model_id.id)])
      
        fd_data = {
            'name': self._def_workflow_state_name,
            'ttype': 'selection',
            'state': 'manual',
            'model_id': self.model_id.id,
            'model': self.model_id.model,
            'modules': self.model_id.modules,
            'tracking': self.tracking,
            'field_description': u'WorkFollow State',
            # 'select_level': '1',
            'selection': str(self.get_state_selection()),
        }
        fd1_data = {
            'name': self._def_workflow_vstate_name,
            'ttype': 'char',
            'state': 'manual',
            'model_id': self.model_id.id,
            'model': self.model_id.model,
            'modules': self.model_id.modules,
            'field_description': u'WorkFollow vState',
            'store': False,
            'compute': """
for record in self:
    record['x_workflow_vstate'] = self.env.context.get('x_workflow_vstate') and self.env.context.get('x_workflow_vstate') or record['x_workflow_state']
            """,
            'depends': self._def_workflow_state_name,
        }
        fd2_data = {
            'name': self._def_workflow_approve_user,
            'ttype': 'char',
            'state': 'manual',
            'model_id': self.model_id.id,
            'model': self.model_id.model,
            'modules': self.model_id.modules,
            'tracking': self.tracking,
            'readonly': True,
            'field_description': u'next approve',
        }
        if fd_id:
            fd_id.write(fd_data)
        else:
            fd_id = fd_obj.create(fd_data)
        if fd_id1:
            fd_id1.write(fd1_data)
        else:
            fd_id1 = fd_obj.create(fd1_data)
        if fd_id2:
            fd_id2.write(fd2_data)
        else:
            fd_id2 = fd_obj.create(fd2_data)

        self.write({'field_id': fd_id.id})
        self.write({'field_id1': fd_id1.id})
        self.write({'field_id2': fd_id2.id})
        return True

    @api.model
    def get_state_selection(self):
        return [(str(i.id), i.name) for i in self.node_ids]

    def event_model(self):
        event_model_list = []
        records = self.env['workflow.base'].search([('isActive','=',True)])
        for rec in records:
            event_model_list.extend([ i.task_model for i in rec.node_ids if i.task_model ])
        self.env['ir.config_parameter'].sudo().set_param('event_model', list(set(event_model_list)))

    def action_no_active(self):
        self.ensure_one()
        self.view_id.unlink()
        self.tree_view_id.unlink()
        #self.widget_view_id.unlink()
        self.field_id1.unlink()
        self.field_id.unlink()
        self.field_id2.unlink()
        self.write({'isActive': False});
        self.event_model()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class workflow_node(models.Model):
    _name = "workflow.node"
    _description = "Workflow Node"
    _order = 'sequence'

    name = fields.Char('Name', required=True, help='A node is basic unit of Workflow')
    sequence = fields.Integer('Sequence',default=0)
    code = fields.Char('Code', required=False)
    descript = fields.Char('descript', required=False)
    workflow_id = fields.Many2one('workflow.base', 'Workflow', required=True, index=True, ondelete='cascade')
    split_mode = fields.Selection([('OR', 'Or'), ('AND', 'And')], 'Split Mode', required=False)
    join_mode = fields.Selection([('OR', 'Or'), ('AND', 'And')], 'Join Mode', required=True, default='OR',
                                 help='OR:anyone input Transfers approved, will arrived this node.  AND:must all input Transfers approved, will arrived this node')
    # 'kind': fields.selection([('dummy', 'Dummy'), ('function', 'Function'), ('subflow', 'Subflow'), ('stopall', 'Stop All')], 'Kind', required=True),

    is_start = fields.Boolean('Workflow Start', help='This node is the start of the Workflow')
    is_stop = fields.Boolean('Workflow Stop', help='This node is the end of the Workflow')
    # 'subflow_id': fields.many2one('workflow', 'Subflow'),
    # 'signal_send': fields.char('Signal (subflow.*)'),
    out_trans = fields.One2many('workflow.trans', 'node_from', 'Out Transfer', help='The out transfer of this node')
    in_trans = fields.One2many('workflow.trans', 'node_to', 'Incoming Transfer', help='The input transfer of this node')
    show_state = fields.Boolean('Show In Workflow', default=False,
                                help="If True, This node will show in Workflow states")
    no_reset = fields.Boolean('Invisible Reset', default=True,
                               help="If True, this Node not display the Reset button, default is True")
    event_need = fields.Boolean('Calender Event&Notify', default=False,
                                help="If true, When Workflow arrived this node, will create a calendar event relation users")
    event_users = fields.Many2many('res.users', 'event_node_ref', 'node_id', 'uid', 'Notify Users')
    # weixin_need = fields.Boolean('Wechat notification', default=True)
    # reset_group_id = fields.Many2one('res.groups', string='reset group')
    field_ids = fields.One2many('odoo.workflow.node.field', 'node_id', string='Fields')

    # 审核类别(审批、会签、知会）
    audit_type = fields.Selection(
        string='Audit Type',
        selection=[('approval', 'Approval'), ('counter_sign', 'Counter Sign'),('notify', 'Notify')],
        default="approval",
    )

    notify = fields.Text('Notify')

    group_ids = fields.Many2many('res.groups', 'group_trans_ref', 'tid', 'gid', 'Groups',
                                 help="The groups who can process this transfer")
    user_ids = fields.Many2many('res.users', 'user_trans_ref', 'tid', 'uid', 'Users',
                                help="The Users who can process this transfer")
    flow_roles = fields.Many2many("workflow.trans.define.users", 'adefine_user_ref', 'tid', 'uid', 'Flow Roles')
    
    condition = fields.Char('Condition', required=True, default='True',
                            help='The check condition of this transfer, default is True')
    x_model_id = fields.Many2one('ir.model', string='Model Ref.', related='workflow_id.model_id', required=True)

    model = fields.Char(related='workflow_id.model')

    is_approve = fields.Boolean('Need calc approve', default=True)
    no_decision = fields.Boolean('No Decision', default=False)

    model_id = fields.Many2one('ir.model', 'Module ID', ondelete="set null", default= lambda self: self.workflow_id.model_id,  help="Select a model that you want to create the Workflow")
    task_model = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    model_view_id = fields.Many2one('ir.ui.view', 'Model View',
                                    help="The form view of the model that want to extend Workflow button on it")

    menu_id = fields.Many2one('ir.ui.menu', string='menu id')
    context = fields.Text(string='context')
    date_deadline = fields.Date(string='date deadline', default= fields.Date.today())
    real_id = fields.Char(string="Real ID", default='self.id')
    task_condition = fields.Char(string="task condition", default="False")
 
    trans_type = fields.Selection([
        ('auto', 'auto process'),
        ('note', 'need note'),
        ('task', 'todo task'),
        ('time', 'Event Detection'),
    ], string='Trans Type', default='auto')
    
    fill = fields.Char('fill color')
    stroke = fields.Char('stroke color')
    strokenWidth  = fields.Integer('width of stocke', default = 1 )
   
    # @api.depends('group_ids')
    # def _compute_xml_groups(self):
    #     for r in self:
    #         data_obj = self.env['ir.model.data'].sudo()
    #         xml_ids = []
    #         records = r.group_ids._origin or r.group_ids
    #         for g in records:
    #             data = data_obj.search([('res_id', '=', g.id), ('model', '=', 'res.groups')])
    #             xml_ids.append(data.complete_name)
    #         r.xml_groups = xml_ids and ','.join(xml_ids) or False

    def compute_approve_ids(self):
        user_ids = []
        if (self.user_ids):
            user_ids = self.user_ids.ids
        if (self.group_ids):
            group_ids = self.group_ids.mapped('users').ids
            user_ids = user_ids + group_ids if user_ids else group_ids
        if (self.flow_roles):
            for code in self.flow_roles.mapped('code'):
                try:
                    define_ids = eval(code)
                except Exception as e:
                    define_ids = []
                    _logger.warning("msg: %s can't eval, %s" % code, e.message)
                    
                if code and len(define_ids) == 0:
                    define_ids = [self.env.user.id]

                user_ids = user_ids + define_ids if user_ids else define_ids
        user_ids = list(dict.fromkeys(user_ids))
        return user_ids
        
    def make_log(self, res_name, res_id, note='', todo=0, trans_id=False):
        return self.env['log.workflow.trans'].create({'name': res_name, 'res_id': res_id, 'trans_id': trans_id, 'node_id': self.id, 'note': note, 'username': self.env.user.name, 'todo':todo})

    def backward_cancel_logs(self, res_id):
        """
        cancel the logs from this node, and create_date after the logs
        """
        log_obj = self.env['log.workflow.trans']
        logs = log_obj.search([('res_id', '=', res_id), ('node_id', '=', self.id)])
        if logs:
            todos = self.env['todo.activity'].search([('res_id','=',res_id),('todo_state','!=','complete')])
            if todos:
                todos.write({'todo_state':'complete'})

            todos = self.env['todo.activity'].search([('res_id','=',res_id),('node_id','=', self.id)])
            if todos:
                newtodos = BaseModel.copy_data(todos)
                self.env['todo.activity'].create(newtodos)
            
            min_date = min([x.create_date for x in logs])
            logs2 = log_obj.search([('res_id', '=', res_id), ('create_date', '>=', min_date)])
            logs.write({'active': False})
            logs2.write({'active': False})

    def check_trans_in(self, res_id):
        self.ensure_one()

        flag = True
        join_mode = self.join_mode
        log_obj = self.env['log.workflow.trans']

        flag = False
        if join_mode == 'OR':
            flag = True
        else:
            in_trans = filter(lambda x: x.is_backward is False, self.in_trans)
            trans_ids = [x.id for x in in_trans]
            logs = log_obj.search([('res_id', '=', res_id), ('trans_id', 'in', trans_ids)])
            log_trans_ids = [x.trans_id.id for x in logs]
            flag = set(trans_ids) == set(log_trans_ids) and True or False

        return flag

    @api.model_create_multi
    def create(self, vals):
        return super().create(vals)

    def make_event(self, name, ids, form_record):

        # 结束当前节点的active
        self.env['mail.activity'].search([('res_id', '=', form_record.id)]).action_done()
        for id in ids:
            self.env['mail.activity'].create({
                'res_id': form_record.id,
                'res_model_id': self.env['ir.model'].sudo()._get(form_record._name).id,
                'summary': _('Workflow approval notification'),
                'note': _('[%s] workflow needs your approval!') % form_record.name,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'user_id': id,
                'date_deadline': date.today()
            })
            # user = self.env['res.users'].browse(id)
            # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            # if 'wxcorp_user_id' in user and self.weixin_need and user.wxcorp_user_id:
            #     url = "{}/web#cids=1&id={}&model={}&view_type=form&menu_id=".format(
            #         base_url, form_record.id, form_record._name
            #     )
            #     text = _('[%s] [%s]\'s [%s] needs approval, please handle it in time! [%s]') % (
            #         fields.Date.context_today(self), self.env.user.name, form_record.display_name, url)
            #     entry = self.env['wx.corp.config'].corpenv()
            #     entry.client.message.send_text(entry.current_agent, user.wxcorp_user_id.userid, text)
        return True

    def btn_load_fields(self):
        # Variables
        field_obj = self.env['ir.model.fields'].sudo()
        for rec in self:
            # Clear Fields List
            rec.field_ids.unlink()
            # Load Fields
            fields = field_obj.search([('model_id', '=', rec.model_id.id)])
            for field in fields:
                rec.field_ids.create({
                    'model_id': rec.model_id.id,
                    'node_id': rec.id,
                    'name': field.id,
                })

    def btn_set_fields_readonly(self):
        if self.field_ids:
            for field in self.field_ids:
                field.write({'readonly': True})

class odoo_workflow_node_field(models.Model):
    _name = 'odoo.workflow.node.field'
    _description = 'Odoo Workflow Node Fields'

    name = fields.Many2one('ir.model.fields', string='Field')
    model_id = fields.Many2one('ir.model', string='Model')
    readonly = fields.Boolean(string='Readonly')
    required = fields.Boolean(string='Required')
    invisible = fields.Boolean(string='Invisible')
    group_ids = fields.Many2many('res.groups', string='Groups')
    user_ids = fields.Many2many('res.users', string='Users')
    node_id = fields.Many2one('workflow.node', string='Node Ref.', ondelete='cascade', required=True)

class workflow_trans(models.Model):
    _name = "workflow.trans"
    _description = "workflow Trans"
    _order = "sequence"

    name = fields.Char("Name", help='A transfer is from a node to other node')
    sequence = fields.Integer('Sequence',default=0)
    node_from = fields.Many2one('workflow.node', 'From Node', required=True, index=True, ondelete='cascade', )
    node_to = fields.Many2one('workflow.node', 'TO Node', required=True, index=True, ondelete='cascade')
    workflow_id = fields.Many2one('workflow.base', 'Workflow', required=True, index=True, ondelete='cascade')
    fill = fields.Char('fill color')
    stroke = fields.Char('stroke color')
    strokenWidth  = fields.Integer('width of stocke', default = 1 )
    condition = fields.Char('Condition', required=True, default='True',
                            help='The check condition of this transfer, default is True')
    is_backward = fields.Boolean(u'Is Reverse', help="Is a Reverse transfer", default=False)

    action_type = fields.Selection([
        ('code', 'Python Code'),
        ('action', 'Server Action'),
        ('win_act', 'Window Action'),
    ], string='Action Type')
    
    py_code = fields.Text(string='Python Code', default=PYTHON_CODE_TEMP)
    server_action_id = fields.Many2one('ir.actions.server', string='Server Action')
    win_act_id = fields.Many2one('ir.actions.act_window', string='Window Action')

    @api.model_create_multi
    def create(self, vals):
        return super().create(vals)    

    def run(self):
        for rec in self:
            if not rec.action_type:
                continue
            run = RunCode(self, self.env)
            func = getattr(run, "_run_%s" % rec.action_type)
            return func()

class defined_users(models.Model):
    _name = "workflow.trans.define.users"
    _description = "workflow define users"
    _order = "sequence"

    name = fields.Char("Name", required=True, help='A transfer is from a node to other node')
    code = fields.Char('Code', required=False)
    current_user_name = fields.Char(string='current user name', compute='_compute_current_user')
    current_user_ids = fields.Many2many('res.users', 'user_define_ref', 'tid', 'uid', 'Current Users')
    sequence = fields.Integer('Sequence')

    def _compute_current_user(self):
        for rec in self:
            user_ids = eval(rec.code)
            rec.current_user_ids = [(6,0,user_ids)]
            rec.current_user_name =",".join(self.env['res.users'].browse(rec.current_user_ids.ids).mapped('name'))

class workflow_buttons(models.Model):
    _name = "workflow.buttons"
    _description = "workflow Buttons"
    _order = "sequence"

    name = fields.Char("Name", required=True)
    group_ids = fields.Many2many('res.groups', string='group ids')
    user_ids = fields.Many2many('res.users', string='user ids')
    workflow_id = fields.Many2one('workflow.base', string='workflow', required=True)
    model = fields.Char(related='workflow_id.model')
    sequence = fields.Integer('Sequence')
    action_type = fields.Selection([
        ('code', 'Python Code'),
        ('action', 'Server Action'),
        ('win_act', 'Window Action'),
    ], string='Active Type')
    py_code = fields.Text(string='Python Code', default=PYTHON_CODE_TEMP)
    server_action_id = fields.Many2one('ir.actions.server', string='Server Action')
    win_act_id = fields.Many2one('ir.actions.act_window', string='Window Action')
    belong_node = fields.Many2one('workflow.node', 'Belone Node', index=True, ondelete='cascade')
    xml_groups = fields.Char(compute='_compute_xml_groups', string='XML Groups')

    @api.onchange('workflow_id')
    def onchange_belong_node(self):
        if 'default_workflow_id' not in self.env.context:
            return {'domain': {'belong_node': []}}
        workflow_id = self.workflow_id and self.workflow_id.id or self.env.context['default_workflow_id']
        node_ids = self.env['workflow.node'].search([('workflow_id', '=', workflow_id)]).ids
        return {'domain': {'belong_node': [('id', 'in', node_ids)]}}

    @api.depends('group_ids')
    def _compute_xml_groups(self):
        data_obj = self.env['ir.model.data'].sudo()
        xml_ids = []
        records = self.group_ids._origin or self.group_ids
        for g in records:
            data = data_obj.search([('res_id', '=', g.id), ('model', '=', 'res.groups')])
            xml_ids.append(data.complete_name)
        self.xml_groups = xml_ids and ','.join(xml_ids) or False

    def run(self):
        for rec in self:
            if not rec.action_type:
                continue
            run = RunCode(self, self.env)
            func = getattr(run, "_run_%s" % rec.action_type)
            return func()

class log_workflow_trans(models.Model):
    _name = "log.workflow.trans"
    _description = "workflow log"

    name = fields.Char('Name')
    trans_id = fields.Many2one('workflow.trans', 'Transfer')
    node_id = fields.Many2one('workflow.node', 'node')
    model = fields.Char(related='node_id.model', string='Model')
    res_id = fields.Integer('Resource ID')
    active = fields.Boolean('Active', default=True)
    trans_type = fields.Selection([
        ('auto', 'auto process'),
        ('note', 'need note'),
        ('task', 'todo task'),
        ('time', 'Event Detection'),
    ], string='Trans Type', default='note')
    username = fields.Char('Approver')
    todo = fields.Integer('todo', default=0)
    note = fields.Text('Note', help="If you want record something for this transfer, write here")

class RunCode:
    def __init__(self, Model, env):
        self.Model = Model
        self.env = env

    def _run_win_act(self):
        # Variables
        cx = self.env.context.copy() or {}
        win_act_obj = self.env['ir.actions.act_window']
        # Run Window Action
        for rec in self.Model:
            action = win_act_obj.with_context(cx).browse(rec.win_act_id.id).read()[0]
            action['context'] = cx
            return action
        return False

    def _run_action(self):
        # Variables
        srv_act_obj = self.env['ir.actions.server']
        # Run Server Action
        for rec in self.Model:
            srv_act_rec = srv_act_obj.browse(rec.server_action_id.id)
            return srv_act_rec.run()

    def _run_code(self):
        # Variables
        cx = self.env.context.copy() or {}
        locals_dict = {
            'env': self.env,
            'model': self.env[cx.get('active_model', False)],
            'record': self.env[cx.get('active_model', False)].browse(cx.get('active_id', 0)),
            'records': self.env[cx.get('active_model', False)].browse(cx.get('active_ids', 0)),
            'user': self.env.user,
            'datetime': datetime,
            'time': time,
            'date': date,
            'timedelta': timedelta,
            'workflow': self.env['workflow.base'],
            'warning': self.warning,
            'syslog': self.syslog,
        }
        # Run Code
        for rec in self.Model:
            try:
                safe_eval(rec.py_code, locals_dict=locals_dict, mode='exec', nocopy=True)
                action = 'action' in locals_dict and locals_dict['action'] or False
                if action:
                    return action
            except Warning as ex:
                raise ex
            except SyntaxError as ex:
                raise UserError(_("Wrong python code defined.\n\nError: %s\nLine: %s, Column: %s\n\n%s" % (
                    ex.args[0], ex.args[1][1], ex.args[1][2], ex.args[1][3])))
        return True

    def warning(self, msg):
        if not isinstance(msg, str):
            msg = str(msg)
        raise UserError(msg)

    def syslog(self, msg):
        if not isinstance(msg, str):
            msg = str(msg)
        _logger.info(msg)