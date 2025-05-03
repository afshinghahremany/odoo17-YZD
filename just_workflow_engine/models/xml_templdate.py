# -*- coding: utf-8 -*-
##############################################################################

bton_contain_template = """
    <div class="o_statusbar_buttons"></div>
"""

btn_template = """
    <button name="workflow_button_action" string="%(btn_str)s"
          context="{'trans_id':'%(trans_id)s', 'workflow_model_name':'%(workflow_model_name)s','model_id':'%(model_id)s'}"
          invisible="x_workflow_vstate != '%(vis_state)s'"
          auto_refresh="1"
          type="object"
          class="%(className)s"/>
"""

button2_template = """
    <button name="workflow_buttons_action" string="%(btn_str)s"
          context="{'buttons_id':'%(buttons_id)s', 'workflow_model_name':'%(workflow_model_name)s','model_id':'%(model_id)s'}"
          invisible="x_workflow_vstate != '%(vis_state)s'"
          type="object"
          class="oe_highlight"/>
"""

btn_show_log_template = """
    <button name="workflow_button_show_log"
          string="%(btn_str)s"
          type="object"
          groups="%(btn_grp)s"
          />
"""

btn_workflow_reset_template = """
    <button name="workflow_button_reset"
          string="%(btn_str)s"
          type="object"
          groups="%(btn_grp)s"
          context="{'workflow_id': %(btn_ctx)s}"
          invisible="x_workflow_state in %(no_reset_states)s"
          />
"""

btn_workflow_link_template = """
    <button name="workflow_button_link"
          string="%(btn_str)s"
          type="object"
          groups="%(btn_grp)s"
          context="{'workflow_id': %(btn_ctx)s}"
          />
"""

arch_template_header = """
    <xpath expr="//header" position="before"></xpath>
"""

arch_template_header_replace = """
    <xpath expr="//header" position="replace"></xpath>
"""

arch_template_no_header = """
    <xpath expr="//form/*" position="before"></xpath>
"""

workflow_contain_template = """
    <div class='o_form_statusbar o_from_workflow_contain position-relative d-flex justify-content-between border-bottom'
    style="background: bisque" 
    invisible=" id == False or x_workflow_state == False "></div>
"""

wfk_field_state_template = """
    <field name="%s" widget="statusbar" readonly="1"  statusbar_visible="%s"/>
"""

wfk_field_vstate_template = """
    <field name="%s"  invisible="1"/>
"""

workflow_field_approve_user = """
    <div class='workflow_field_approve_user' style="display:flex;align-items: center;"> 
    <label for="%s" invisible=" %s == False"/>  <field name="%s" readonly="1"/></div>
"""

wfk_field_note_template = """
    <span class="oe_inline">Note:<field name="%s" class="oe_inline" string="sss"/></span>
"""

tree_template_inhert = """
    <xpath expr="//tree" position="inside"></xpath>
"""

widget_template = """
<form>
  <group>
    <field name="x_workflow_approve_user" string='工作流节点' widget="diagram"/>
    <field name="x_workflow_state" invisible="1"/>
  </group>
  <footer> <button name="write" type="object" string="Save" invisible='1'/>   </footer>
</form>
"""