import logging
import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ActivityStage(models.Model):
    _name = 'todo.mail.activity.stage'
    _description = 'activity stage'
    _order = 'sequence asc'

    name = fields.Char('名称')
    sequence = fields.Integer('序号')

class ActivityTodo(models.Model):
    _name = 'todo.activity'
    _description = 'my todo task'
    _inherit = 'mail.thread'
    _order = 'read_state desc,create_date desc,date_deadline asc'
    _rec_name = 'title_display'

    title = fields.Char(required=True)
    summary = fields.Char()
    description = fields.Char()
    title_display = fields.Char(compute='_compute_title_display', store=True)
    sequence = fields.Integer('Sequence')
    stage_id = fields.Many2one('todo.mail.activity.stage')
    color = fields.Integer(string='Color Index')
    view_id = fields.Integer('view_id')
    send_user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    read_state = fields.Selection([("unread", "unread"), ("read", "read")],  default='unread')
    todo_state = fields.Selection([('todo', 'todo'), ('complete', 'complete')],  default='todo', copy=False)
    menu_id = fields.Many2one('ir.ui.menu', string='menu_id')
    context = fields.Char()
    image = fields.Image(related='menu_id.web_icon_data', string='icon')
    user_ids = fields.Many2many('res.users')
    executor = fields.Many2one('res.users', string='Executor', copy=False)
    date_deadline = fields.Date(string='deadline')
    is_complete = fields.Boolean(default=False)
    res_model = fields.Char(index=True, related='res_model_id.model', store=True)
    res_model_id = fields.Many2one('ir.model', 'Model')
    res_id = fields.Many2oneReference(index=True, required=True, model_field='res_model')
    source = fields.Char()
    background_color = fields.Char(compute='_compute_background_color')
    real_model = fields.Char()
    real_id = fields.Integer()

    note_type = fields.Selection([('one', 'Review comments'), ('many', 'Countersign opinion'), ('add', 'Additional comments')], default='one')
    trans_id = fields.Integer()
    node_id = fields.Integer()
    notes = fields.Text(copy=False)

    def write(self, values):
        res = super(ActivityTodo, self).write(values)
        return res

    @api.model_create_multi
    def create(self, vals):
        result = super(ActivityTodo, self).create(vals)
        if not result.title_display:
            self._compute_title_display()
        return result

    @api.depends('read_state')
    def _compute_background_color(self):
        for record in self:
            if record.read_state == 'read':
                record.background_color = '0'
            else:
                record.background_color = ''

    @api.depends('title', 'summary', 'description')
    def _compute_title_display(self):
        for record in self:
            displays = []
            if record.summary:
                displays.append(record.summary)
            if record.description:
                displays.insert(0, record.description)
            elif record.title:
                displays.insert(0, record.title)
            record.title_display = '-'.join(displays)

    @api.depends("todo_state", "send_user_id")
    def _compute_button_state(self):
        for record in self:
            if record.send_user_id == self.env.user and record.todo_state == 'todo':
                record.is_complete = True
                continue
            if record.send_user_id == self.env.user:
                record.is_complete = False
                continue
            if record.todo_state == 'todo':
                record.is_complete = True
            else:
                record.is_complete = False

    #@api.model
    #def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #    groups = []
    #    stages = self.env['todo.mail.activity.stage']
    #    stages = stages.search([])
    #    if stages:
    #        for stage in stages:
    #            stageid = stage.id
    #            domains = [("stage_id", "=", stageid)] + domain
    #            stagename = stage.name
    #            stage_id_count = self.search_count(domains)
    #            group = {
    #                '__domain': domains,
    #                'stage_id': (stageid, stagename),
    #                'stage_id_count': stage_id_count,
    #                'color': False,
    #            }
    #            groups.append(group)
    #    return groups

    def btn_view_detail(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": self.real_model,
            "res_id": self.real_id,
            "view_id": self.view_id,
        }
        self.read_state = 'read'
        if self.context:
            context = json.loads(self.context)
            context.update({'workflow_todo_id': self.id})
            context.update({'active_model': self.real_model})
            context.update({'active_id': self.real_id})
            context.update({'trans_id': self.trans_id})
            action.update({'context': context})
        return action

    def btn_complete(self):
        self.todo_state = 'complete'
        action = self.env.ref('just_todo.action_hn_todo_activity_todo').read()[0]
        action.update({'target': 'main'})
        return action

    def compute_coordination_source(self, res_modelId, resId):
        res_model_id = self.env['ir.model'].sudo().browse(res_modelId)
        res_model = res_model_id.model
        Source = self.env[res_model]
        source_id = Source.browse(resId)
        try:
            source = source_id.name
        except:
            source = ''
        return source

    # 推荐用新接口调用发起待办
    # 重复待办不会创建
    def add_todo(self,
                 record_id,
                 date_deadline,
                 user_ids,
                 title,
                 summary,
                 view_id,
                 stage,
                 menu_id,
                 real_model,
                 real_id,
                 context=False,
                 note_type='one',
                 trans_id=False,
                 node_id=False,
                 ):
        '''
        param:
            res_modelId: 目标模型id,
            resId: 目标记录id,
            date_deadline: 到期日期,
            userIds: 分派给用户[id],
            title: 商机名称,
            summary: 任务描述,
            viewId: 目标视图id,
            stageId: 目标stageid
                {
                    'stage_coordination': '协同',
                    'stage_contract': '合同',
                    'stage_cost': '成本预提',
                    'stage_deliver_purchase': '发货与采购',
                    'stage_contract_decompose': '合同执行‘
                    'stage_bill': '开票',
                    'stage_pay_back': '回款'
                },
            menuId: 目标菜单id取图标用,
            description: 协同用,
            real_model: 真实的来源模型名字(self._name)，区别于res_modelId是为了要通过执行进入的模型id,
            real_id: 真是的来源模型id(self.id), 区别于resId是为了要通过执行进入的模型id,
        '''
        IrModel = self.env['ir.model'].sudo()
        res_model_id = IrModel.search([('model', '=', record_id._name)], limit=1)

        if not res_model_id:
            raise UserError(f'The corresponding module {record_id._name} is not found')
        if 'just_todo.' not in stage:
            stage = f'just_todo.{stage}'
        stage_id = self.env.ref(stage, False)
        if not stage_id:
            raise UserError(f'Stage parameter error, corresponding stage type {stage} not found')
        #view_id = self.env.ref(view, False)
        #if not view_id:
        #    raise UserError('View parameter error, view {view_id} not found')
        ##menu_id = self.env.ref(menu, False)
        #if not menu_id:
        #    raise UserError('菜单参数错误，未找到菜单 {menu_id}')
        if context:
            context = json.dumps(context)

        # record_ids = self.search([('res_id', '=', record_id.id), ('res_model_id', '=', res_model_id.id),
        #                           ('user_id', 'in', user_id), ('real_model', '=', real_model),
        #                           ('real_id', '=', real_id), ('todo_state', '=', 'todo')])
        #if record_ids:
        #    _logger.warn('不可重复创建任务')
        #    return

        source = self.env[real_model].browse(real_id)
        if note_type == 'one':
            for uid in user_ids:
                self.create({
                'res_model_id': res_model_id.id,
                'res_id': record_id.id,
                'date_deadline': date_deadline,
                'user_ids': [(6,0,[uid])],
                'title': title,
                'summary': summary,
                'view_id': view_id and view_id.id or False,
                'stage_id': stage_id.id,
                'menu_id': menu_id and menu_id.id or False,
                'source': source.name,
                'real_model': real_model,
                'real_id': real_id,
                'context': context,
                'note_type': note_type,
                'trans_id': trans_id,
                'node_id': node_id,
            })
        elif note_type == "many":
            self.create({
                'res_model_id': res_model_id.id,
                'res_id': record_id.id,
                'date_deadline': date_deadline,
                'user_ids': [(6,0,user_ids)],
                'title': title,
                'summary': summary,
                'view_id': view_id and view_id.id or False,
                'stage_id': stage_id.id,
                'menu_id': menu_id and menu_id.id or False,
                'source': source.name,
                'real_model': real_model,
                'real_id': real_id,
                'context': context,
                'note_type': note_type,
                'trans_id': trans_id,
                'node_id': node_id,
            })    

    def done(self, record_id=False, notes=''):
        '''
        完成
        :params record_id 关联任务对象
        :params user_id 待办人
        :source_id 来源对象，用来与其他相关内容区分
        '''
        self.ensure_one()
        self.with_context({}).write({'todo_state': 'complete', 'executor': self.env.user.id, 'notes': notes})

        odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        trans = self.env['workflow.trans'].browse(self.trans_id)
        
        if trans.node_to.event_need and trans.node_to.event_users:
           users = trans.node_to.event_users
           notification_ids = [(0, 0, {'res_partner_id': user.partner_id.id, 'notification_type': 'inbox'}) for user in users]
           self.executor.partner_id.message_post(
                body='[ %s ] %s ( %s ) -> %s' % (self.source,  trans.name, notes, trans.node_to.name),
                message_type='notification', 
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
                author_id=self.executor.partner_id.id,
                notification_ids=notification_ids,
                auto_delete=False,
            )

    def finish_todo(self, res_model, resId, userId=None, title=None, description=None, real_model=None, real_id=None):
        '''
        param:
            res_model: 模型名(str),例如'crm.lead',
            res_id: 创建时传入的记录id,
            提示：userId和title需要指定一个
            userId: 执行人id，
            title: 非必传，在一个模型里无法区分多个待办信息的时候用title区分，title是显示的标题中 - 前面的部分
        '''

        domain = [('res_model', '=', res_model), ('res_id', '=', resId)]
        if userId:
            domain += [('user_id', '=', userId)]
        elif description:
            domain += [('description', '=', description)]
        elif title:
            domain += [('title', '=', title)]
        else:
            raise UserError('The executor and title need to specify either one')

        if real_id and real_model:
            domain = [('real_model', '=', real_model), ('real_id', '=', real_id)]

        todo_ids = self.search(domain)
        for todo_id in todo_ids:
            todo_id.todo_state = 'complete'

    def btn_feedback(self):
        self.ensure_one()
        view_id = self.env.ref('just_todo.hn_todo_activity_form')
        return {
            'name': _('Discuss'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'view_id': view_id.id,
            'res_id': self.id,
        }
