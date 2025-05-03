import logging
import odoo.http as http
import datetime

from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class DiagramPlusView(http.Controller):

    # Just Copy+Paste+Edit of original Odoo's method
    # pylint: disable=redefined-builtin,too-many-locals,too-many-statements
    # pylint: disable=too-many-branches
    @http.route('/web_diagram_plus/diagram/get_diagram_info',
                type='json', auth='user')
    def get_diagram_info(self, id, model, node, connector,
                         src_node, des_node, label, **kw):
        visible_node_fields = kw.get('visible_node_fields', [])
        invisible_node_fields = kw.get('invisible_node_fields', [])
        node_fields_string = kw.get('node_fields_string', [])
        connector_fields = kw.get('connector_fields', [])
        connector_fields_string = kw.get('connector_fields_string', [])
        active_id = kw.get('active_id',  False)
        active_model = kw.get('active_model', False)

        # bgcolors = {}
        # shapes = {}
        # bgcolor = kw.get('bgcolor', '')
        # bg_color_field = kw.get('bg_color_field', '')
        # fg_color_field = kw.get('fg_color_field', '')
        # shape = kw.get('shape', '')

        # if bgcolor:
        #     for color_spec in bgcolor.split(';'):
        #         if color_spec:
        #             colour, color_state = color_spec.split(':')
        #             bgcolors[colour] = color_state

        # if shape:
        #     for shape_spec in shape.split(';'):
        #         if shape_spec:
        #             shape_colour, shape_color_state = shape_spec.split(':')
        #             shapes[shape_colour] = shape_color_state

        ir_view = http.request.env['ir.ui.view']
        graphs = ir_view.graph_get(int(id), model, node, connector, src_node,
                                   des_node, label, (140, 180))

        nodes = graphs['nodes']
        transitions = graphs['transitions']
        diagram = graphs['diagram']
        isolate_nodes = {}
        for blnk_node in graphs['blank_nodes']:
            isolate_nodes[blnk_node['id']] = blnk_node

        connectors = {}
        list_tr = []

        for tr in transitions:
            list_tr.append(tr)
            connectors.setdefault(tr, {
                'id': int(tr),
                's_id': transitions[tr][0],
                'd_id': transitions[tr][1]
            })

        connector_model = http.request.env[connector]
        data_connectors = connector_model.search(
            [('id', 'in', list_tr)]).read(connector_fields)

        for tr in data_connectors:
            transition_id = str(tr['id'])
            _sourceid, label = graphs['label'][transition_id]
            t = connectors[transition_id]
            t.update(
                source=tr[src_node][1],
                destination=tr[des_node][1],
                options={},
                signal=label
            )

            for i, fld in enumerate(connector_fields):
                t['options'][connector_fields_string[i]] = tr[fld]

        flowstate = {'logs': [], 'transIds':[], 'nodesIds':[]}
        if (active_model != model):
            flowstate['logs'] = http.request.env['log.workflow.trans'].search_read([('res_id', '=', active_id), ('model', '=', active_model)],['trans_id','node_id','note','create_date','username'], order="create_date")
            flowstate['transIds'] = [x['trans_id'][0] for x in flowstate['logs']]
            flowstate['nodesIds'] = [x['node_id'][0] for x in flowstate['logs']]
            
            for i, x in enumerate(flowstate['logs']):
                flowstate['logs'][i]['create_date'] = (flowstate['logs'][i]['create_date']).strftime("%m/%d %H:%M")

            active_rec = http.request.env[active_model].browse(active_id)
            flowstate['currentNode'] = int(active_rec.x_workflow_state)

        _id, name = http.request.env[model].browse([id]).name_get()[0]
        return dict(nodes=nodes,
                    conn=connectors,
                    diagram=diagram,
                    display_name=name,
                    flowstate=flowstate,
                    parent_field=graphs['node_parent_field'])
