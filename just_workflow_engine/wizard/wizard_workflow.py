# -*- coding: utf-8 -*-
##############################################################################

from odoo import api, fields, models, _
import datetime

class wizard_workflow_message(models.TransientModel):
    _name = 'wizard.workflow.message'
    _description = 'Workflow Message'
    
    name = fields.Text(u'Note', default=_('Agree'))
    logType = fields.Integer('logType', default=0)
    user_ids = fields.Many2many('res.users', string='加签人')
    note_type = fields.Selection([
        ('Agree', 'Agree'),
        ('Stop', 'Refuse and Stop'),
        ('Back', 'Refuse and Back To'),
    ], string='Trans Type', default=_('Agree'))
    back_to = fields.Selection(selection='_selection_filter', default='start', string='Back to')

    @api.model
    def _selection_filter(self):
        res_field = [('start', _('Workflow Restart')), ('previous', _('Previous Node'))]
        ctx = self.env.context
        nodes = self.env['log.workflow.trans'].search(['&', ('res_id', '=', ctx.get('active_id')),('trans_type', '=', 'note')])
        trans_name = {str(r.node_id.id):r.node_id.name for r in nodes if r.trans_id.node_from.trans_type == 'note'}
        for (key, node) in trans_name.items():
            res_field.append((key, node))
        return res_field

    def _compute_binding_info(self):
        type_dict = dict(self.fields_get(allfields=['note_type'])['note_type']['selection'])
        self.bind_info = type_dict[self.note_type]

    def _compute_backto_info(self):
        type_dict = dict(self.fields_get(allfields=['back_to'])['back_to']['selection'])
        return type_dict[self.back_to]
       
    def _compute_no_decision(self):
        ctx = self.env.context
        note_t = self.env['workflow.trans'].browse(int(ctx.get('trans_id')))
        self.no_decision = note_t.node_to.no_decision

    bind_info = fields.Char(compute='_compute_binding_info')
    no_decision = fields.Boolean(compute='_compute_no_decision')

    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        note_t = self.env['workflow.trans'].browse(int(ctx.get('trans_id')))
        node = note_t.node_from
        trans_id = note_t.id
        note = node.name + _('Review comments')
        record = self.env[ctx.get('active_model')].browse(ctx.get('active_id'))

        auto_note = self.name == _('Agree') and self.bind_info or self.name
        auto_note = self.bind_info + self._compute_backto_info() if self.note_type == 'Back' else auto_note
        auto_note = self.bind_info if self.note_type == 'Stop' else auto_note      
        
        todo_id = ctx.get('workflow_todo_id')
        if (todo_id):
            todo = self.env['todo.activity'].browse(int(todo_id))
            todo.done(notes=auto_note)
            note = node.name + todo.summary

            # add todo for countersignature
            if (self.user_ids):
                self.env['todo.activity'].add_todo(
                     record,
                    datetime.date.today(),
                    [x.id for x in self.user_ids],
                    node.name,
                     _('Countersignature opinion'),
                     node.workflow_id.view_id,
                    'stage_approve',
                     self.env.ref("just_workflow_engine.menu_workflow_root", False),
                     ctx.get('active_model'),
                     ctx.get('active_id'),
                     context = ctx,
                     note_type = 'one',
                     trans_id = todo.trans_id,
                     node_id = node.id,)

            todos = self.env['todo.activity'].search(['&',('trans_id','=',todo.trans_id),'&',('res_id','=',ctx.get('active_id')),('todo_state','!=','complete')])          
            if (todos):
                node.make_log(record.name, record.id, note + ':' + auto_note, todo_id, todo.trans_id)
                return True

        if (self.note_type == 'Back' and not self.no_decision):
            if self.back_to == 'start':
                node.make_log(record.name, record.id, note + ':' + auto_note, todo_id, trans_id)
                record.workflow_button_reset(node.workflow_id.id)
                return True
            elif self.back_to == 'previous':
                type_dict = dict(self.fields_get(allfields=['back_to'])['back_to']['selection'])
                if len(type_dict) == 2:
                   node.make_log(record.name, record.id, note + ':' + auto_note, todo_id, trans_id)
                   record.workflow_button_reset(node.workflow_id.id)
                   return True
                else:
                   back_to_state = list(type_dict.keys())[-1]             
            else:
                back_to_state = self.back_to

            node = self.env['workflow.node'].browse(int(back_to_state))
            node.make_log(record.name, record.id, note + ':' + auto_note, todo_id, trans_id)
            node.backward_cancel_logs(record.id)
            record.write({'x_workflow_state': back_to_state})
            return True

        if (self.note_type == 'Stop' and not self.no_decision):
            record.workflow_button_stop(node.workflow_id.id)
            todos = self.env['todo.activity'].search(['&',('trans_id','=',trans_id),'&',('res_id','=',ctx.get('active_id')),('todo_state','!=','complete')])
            todos.write({'todo_state':'complete'})
            return True
        
        record.with_context(trans_id = trans_id, x_workflow_vstate=False).workflow_action(note + ':' + auto_note)
        return True
