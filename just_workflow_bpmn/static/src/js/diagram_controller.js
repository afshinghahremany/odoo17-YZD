/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillUnmount, useEffect, useRef, onMounted, useState } from "@odoo/owl";
import { standardViewProps } from "@web/views/standard_view_props";
import { jsonrpc } from "@web/core/network/rpc_service";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { useModelWithSampleData } from "@web/model/model";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Layout } from "@web/search/layout";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';

export class DiagramPlusController extends Component {
    static template = 'DiagramControllView';
	static components = { Layout, SearchBar, CogMenu};

	setup() {
		this.rpc = jsonrpc;
        this.displayDialog = useOwnedDialogs();
		this.props.className = 'o_diagram_plus_view h-100';
		this.action = useService("action");
		this.dialog = useService("dialog");

		this.domain = this.props.domain || [];
		this.context = this.props.context;
		this.ids = this.props.ids;
		this.currentId = this.props.currentId;
		this.iTime = null;
		this.root = $(useRef("root"));
		this.mode = this.context.form_view_initial_mode;

		this.archInfo = this.props.archInfo;
		const { create, edit } = this.archInfo.activeActions;
		this.canCreate = create && !this.props.preventCreate && this.mode != 'view';
		this.canEdit = edit && !this.props.preventEdit;

		onMounted(() => {
            this._fetchDiagramInfo();
		});
	};

	async _rpc(params) {
		const url = `/web/dataset/call_kw/${params.model}/${params.method}`;
		params.kwargs = { context: this.props.context };
        return await this.rpc(url, params);
	}

    /**
     * @private
     * @param {any} record
     * @returns {Promise}
     */
    _fetchDiagramInfo() {
        var self = this;
		this.res_id = this.context.workflow_id ? this.context.workflow_id : this.props.resId ? this.props.resId : this.props.resIds[0];
        this.rpc('/web_diagram_plus/diagram/get_diagram_info',
            {
                id: this.res_id,
                model: this.props.resModel,
                node: this.props.modelParams.node_model,
                connector: this.props.modelParams.connector_model,
                src_node: this.props.modelParams.connectors.attributes["source"].nodeValue,
                des_node: this.props.modelParams.connectors.attributes["destination"].nodeValue,
                label: this.props.modelParams.connectors.attributes["label"].nodeValue || false,
                // bgcolor: this.props.nodes.attributes["bgcolor"].nodeValue,
                // bg_color_field: "",
                // fg_color_field: "",
                // shape: this.props.nodes.attributes["shape"].nodeValue,
                visible_nodes: this.props.modelParams.visible_nodes,
                invisible_nodes: this.props.modelParams.invisible_nodes,
                node_fields_string: this.props.modelParams.node_fields_string,
                connector_fields_string: this.props.modelParams.connector_fields_string,
				active_id: this.context.active_id,
				active_model: this.context.active_model,   
            }
        ).then(function (data) {
            self.props.propsnodes = data.nodes;
            self.props.edges = data.conn;
            self.props.diagram = data.diagram;
            self.props.parent_field = data.parent_field;
            self.props.flowstate = data.flowstate;
			self.start();
			self._renderView();
        });
    };

	async saveDiagram(params = {}) {
		var self = this;
		var Modeling = this.$diagram.get("modeling");
		var diagram = params.context ? params.context.diagram : params.diagram;

		var changedType = function(type) {
			var newType = {type: type};
			var exceptType = /.*(Event)$/;
			if (exceptType.test(type)) newType.eventDefinitionType = 'bpmn:SignalEventDefinition';
			const newElementData = newType;
			var replace = self.$diagram.get('bpmnReplace')
			return replace.replaceElement(diagram, newElementData)
		};
	
		var defineType={'note': 'bpmn:UserTask','time':'bpmn:IntermediateThrowEvent','task':'bpmn:BusinessRuleTask'};
		if (defineType[params.data.trans_type] && defineType[params.data.trans_type] !== diagram.type) {
			diagram = changedType(defineType[params.data.trans_type]);
		}

		Modeling.updateProperties(diagram, { bpmnId: params.data.id, name: params.data.name });
		Modeling.setColor(diagram, { fill: params.data.fill ? params.data.fill : null, stroke: params.data.stroke ? params.data.stroke : null, strokenWidth: params.data.strokenWidth });
	    
		this._flowDbSave();
	};

	// 下载xml/svg
	download(type, data, name) {
		const a = document.createElement('a');
		name = name || `diagram.${type}`;

		a.setAttribute(
			'href',
			`data:application/bpmn20-xml;charset=UTF-8,${encodeURIComponent(data)}`
		);
		a.setAttribute('target', '_blank');
		a.setAttribute('dataTrack', `diagram:download-${type}`);
		a.setAttribute('download', name);

		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
	};

	async _downbpmn(e) {
		this.$diagram.saveXML({ format: true }, (err, xml) => {
			this.download('bpmn', xml);
		});
	};

	async _downsvg(e) {
		this.$diagram.saveSVG({ format: true }, (err, xml) => {
			this.download('svg', xml);
		});
	};

	async _importbpmn(e) {
		this.dialog.add(ConfirmationDialog, {
            body: _t('import will remove all of the workflow diagram, please confirm!'),
            confirm: async () => {
                $('#fileSelector').click();
            },
            cancel: () => {},
        });
	};

	processFileSelected(e) {
		var self = this;
		var file = e.currentTarget.files[0];
		$("#fileSelector").val("");

		function importSuccessCallback(xml) {
			self.$diagram.importXML(xml, err => {
				if (err) {
					alert(_t('Import bpmn file error, please check the content of file.'));
				}
			});
		};

		var reader = new FileReader();
		reader.onload = function () {
			importSuccessCallback(this.result);
		};
		reader.readAsText(file);
	};

	async _flowsave(e) {
		var self = this;
		var elements = self.$diagram.get("elementRegistry")._elements;
		var Modeling = self.$diagram.get("modeling");
		var exceptType = /.*(Task|Flow|Event|Gateway)$/;
		var onlysave = true;
		if (e.type === 'click') {
			$.map(elements, function (el) {
				var element = el.element;
				var bpmnId = parseInt(element.di.bpmnElement.$attrs.bpmnId);
				var name = element.di.bpmnElement.name;
				if (exceptType.test(element.type) && isNaN(bpmnId)) {
					Modeling.setColor(element, { stroke: 'red', });
					onlysave = false;
					if (element.type.indexOf('Flow') > 0) {
						var fromid = parseInt(element.source.di.bpmnElement.$attrs.bpmnId);
						var toid = parseInt(element.target.di.bpmnElement.$attrs.bpmnId);
						if (fromid && toid) self._onAddEdge({name: name, source_id: fromid, dest_id: toid, e: element });
					} else {
						self._addNode({ name: name, is_start: element.type === 'bpmn:StartEvent', is_stop: element.type === 'bpmn:EndEvent', e: element })
					}
				}
			});

			if (onlysave) this._flowDbSave();
		}
	};

	async _flowDbSave(e) {
		var self = this;
		clearTimeout(this.iTime); //只要触发就清除
		var diagram = await self.$diagram.saveXML({ format: true });
		this.iTime = setTimeout(() => {  // 500ms 防抖动处理
			this._rpc({
				model: self.props.resModel,
				method: 'write',
				args: [self.props.resId, {
					diagram: diagram,
				}],
			})
		}, 500);
	};

	// --------------------------------------------------------------------
	// Private
	// --------------------------------------------------------------------

	/**
	 * Creates a popup to add a node to the diagram
	 *
	 * @private
	 */
	_addNode(event) {
		var self = this;
		var name = event.name ? event.name : 'new';
		var diagramel = event.e;
		this._rpc({
			model: self.props.modelParams.node_model,
			method: 'create',
			args: [{
				name: name,
				workflow_id: self.props.resId,
				is_start: event.is_start,
				is_stop: event.is_stop,
			}],
			kwargs: { context: self.props.context },
		}).then(function (id) {
			self.saveDiagram({ data: { id: id, name: name }, diagram: diagramel });
		});
	};

	// --------------------------------------------------------------------
	// Handlers
	// --------------------------------------------------------------------

	/**
	 * Custom event handler that opens a popup to add an edge from given
	 * source and dest nodes.
	 *
	 * @private
	 * @param {OdooEvent} event
	 */
	_onAddEdge(event) {
		var self = this;
		var name = event.name ? event.name : null;
		var diagramel = event.e;
		this._rpc({
			model: self.props.modelParams.connector_model,
			method: 'create',
			args: [{
				name: name,
				workflow_id: self.props.resId,
				node_from: event.source_id,
				node_to: event.dest_id,
			}],
			kwargs: { context: self.props.context },
		}).then(function (id) {
			self.saveDiagram({ data: { id: id, name: name }, diagram: diagramel });
		});
	};

	_onUpdateEdge(event) {
		var self = this;
		this._rpc({
			model: self.props.modelParams.connector_model,
			method: 'write',
			args: [event.id, {
				node_from: event.source_id,
				node_to: event.dest_id,
			}],
		}).then(this._flowDbSave.bind(this));
	};
	/**
	 * Custom event handler that opens a popup to edit an edge given its id
	 *
	 * @private
	 * @param {OdooEvent} event
	 */
	_onEditEdge(event) {
		var self = this;
		var id = parseInt(event.id, 10);
		this.context.diagram = event.e;
		this.displayDialog(FormViewDialog, {
			resModel: self.props.modelParams.connector_model,
			resId: id,
			context: this.context,
			title: _t("Open:") + " " + _t('Transition'),
			onRecordSaved: (r) => { 
				var data = r.data;
				data.id = id;
				var params = { data: data, diagram: event.e};
				self.saveDiagram(params);
			},
		})
	};

	/**
	 * Custom event handler that opens a popup to edit the content of
	 * a node given its id
	 *
	 * @private
	 * @param {OdooEvent} event
	 */
	_onEditNode(event) {
		var self = this;
		var id = parseInt(event.id, 10);
		this.context.diagram = event.e;
		this.displayDialog(FormViewDialog, {
			resModel: self.props.modelParams.node_model,
			resId:id,
			context: this.context,
			title: _t("Open:") + " " + _t('Activity'),
			onRecordSaved: (r) => { 
				var data = r.data;
				data.id = id;
				var params = { data: data, diagram: event.e};
				self.saveDiagram(params);
			},
		})
	};

	/**
	 * Custom event handler that removes an edge given its id
	 *
	 * @private
	 * @param {OdooEvent} event
	 */
	_onRemoveEdge(event) {
		var self = this;
		self._rpc({
			model: self.props.modelParams.connector_model,
			method: 'unlink',
			args: [event.id],
		}).then(this._flowDbSave.bind(this));
	};

	/**
	 * Custom event handler that removes a node given its id
	 *
	 * @private
	 * @param {OdooEvent} event
	 */
	_onRemoveNode(event) {
		var self = this;
		self._rpc({
			model: self.props.modelParams.node_model,
			method: 'unlink',
			args: [event.id],
		}).then(this._flowDbSave.bind(this));
	};

	_onEditLabel(event) {
		var modelname = e.type === 'bpmn:SequenceFlow' ? self.props.modelParams.connector_model : self.props.modelParams.node_model;
		this._rpc({
			model: modelname,
			method: 'write',
			args: [event.id, {
				name: event.text
			}],
		}).then(this._flowDbSave.bind(this));
	};

	/**
	 * @override
	 * @returns {Promise}
	 */
	start() {
		var $header = this.root.filter('.o_diagram_plus_header');
		$.each(this.props.modelParams.labels, function (label) {
			$header.append($('<span>').html(label));
		});
	};

	// --------------------------------------------------------------------
	// Private
	// --------------------------------------------------------------------

	/**
	 * @override
	 * @returns {Promise}
	 */
	async _renderView() {
		var self = this;
		var nodes = this.props.nodes;
		var edges = this.props.edges;
		var id_to_node = {};

		var bpmnParms = {
			container: this.root[0].el,
			keyboard: {
				bindTo: window
			},
			autoplace: false,
			// additionalModules : [
			// 	{
			// 		replaceMenuProvider: ['value', ''],
			// 	}
			// ]
		};

		if (self.mode === 'view') {
			bpmnParms.additionalModules = [
				{
					translate: ['value', ''],
					paletteProvider: ["value", ''],//禁用/清空左侧工具栏
					labelEditingProvider: ["value", ''],//禁用节点编辑
					contextPadProvider: ["value", ''],//禁用图形菜单
					bendpoints: ["value", {}],//禁用连线拖动
					move: ['value', '']//禁用单个图形拖动
				}
			];
		};

		// modeler instance
		var bpmnModeler = new BpmnJS(bpmnParms);

		/**
		 * Open diagram in our modeler instance.
		 *
		 * @param {String} bpmnXML diagram to display
		 */
		async function openDiagram(bpmnXML) {
			// import diagram
			try {
				await bpmnModeler.importXML(bpmnXML);
				// access modeler components
				var canvas = bpmnModeler.get('canvas');
				var overlays = bpmnModeler.get('overlays');
				var elementRegistry = bpmnModeler.get('elementRegistry');
				var Modeling = bpmnModeler.get("modeling");
				if (self.mode === 'view') {
					var elements = bpmnModeler.get("elementRegistry").getAll();
					$.map(elements, function (element) {
						var bpmnId = parseInt(element.di.bpmnElement.$attrs.bpmnId);
						if (element.type.indexOf('Flow') > 0 && self.props.flowstate.transIds.includes(bpmnId)) {
							Modeling.setColor(element, { stroke: 'blue', strokenWidth: 2 });
							var indexOfTrans = self.props.flowstate.transIds.indexOf(bpmnId);
							var transname = self.props.flowstate.logs[indexOfTrans].trans_id[1];
							var indexName = (indexOfTrans + 1) + '-' + (transname  ?  transname : self.props.flowstate.logs[indexOfTrans].node_id[1]);
							Modeling.updateProperties(element, { 'name': indexName });
						} else if (self.props.flowstate.nodesIds.includes(bpmnId)) {
							Modeling.setColor(element, { fill: 'green', strokenWidth: 2 });
						}
						if (bpmnId == self.props.flowstate.currentNode) Modeling.setColor(element, { fill: 'pink', strokenWidth: 2 });
					});
					bpmnModeler.on('element.hover', e => {
						var bpmnId = parseInt(e.element.di.bpmnElement.$attrs.bpmnId);
						var idIndex = self.props.flowstate.nodesIds.indexOf(bpmnId);
						if (bpmnId && e.element.type.indexOf('Flow') < 0 && idIndex > -1) {
							const $overlayHtml = $('<div class="tipBox">' + self.props.flowstate.logs[idIndex].username + ':' + self.props.flowstate.logs[idIndex].create_date + '\r\n' + self.props.flowstate.logs[idIndex].note + '</div>');
							overlays.add(e.element.id, {
								position: { top: e.element.height, left: 0 },
								html: $overlayHtml
							});
						}
					});
					bpmnModeler.on('element.out', () => {
						overlays.clear();
					});
				} else {
					// zoom to fit full viewport
					//canvas.zoom('fit-viewport');

					const events = ['element.dblclick', 'shape.added', 'shape.removed', 'connection.added', 'connection.removed']
					events.forEach(function (event) {
						bpmnModeler.on(event, e => {
							console.log(event, e);
							var shape = e.element ? elementRegistry.get(e.element.id) : e.shape;
							var bpmnId = parseInt(shape.di.bpmnElement.$attrs.bpmnId);
							var name = shape.di.bpmnElement.name;
							var useType = /.*(Task|Flow|Event|Gateway)$/;
							if (event === 'element.dblclick') {
								if (useType.test(shape.type)) {
									self.double_click_callback({
										type: shape.type,
										id: bpmnId,
										e: shape,
									});
								}
								if (shape.type === 'bpmn:SubProcess') {
									self.open_subflow({
										id: bpmnId,
									});
								}
							} else if (event === 'shape.added' || event === 'connection.added') {
								if (useType.test(shape.type)) {
									self.new_element_callback({
										type: event,
										name: name,
										e: shape
									});
								}
							} else if (event === 'shape.removed' || event === 'connection.removed') {
								if (bpmnId) {
									self.destruction_callback({
										type: event,
										id: bpmnId
									});
								}
							}
						});
					});
					const modelingevent = ['commandStack.connection.reconnect.postExecute'];
					modelingevent.forEach(function (event) {
						bpmnModeler.on(event, e => {
							console.log(event, e);
							var elementRegistry = bpmnModeler.get('elementRegistry');
							var shape = null;
							var bpmnId = null;
							if (event === 'commandStack.element.updateLabel.postExecuted') {
								shape = e.context.element;
								bpmnId = parseInt(shape.di.bpmnElement.$attrs.bpmnId);
								if (bpmnId && e.context.newLabel != 'undefined') self.edit_label_callback({ id: bpmnId, label: e.context.newLabel, e: shape });
							} else if (event === 'commandStack.connection.reconnect.postExecute') {
								shape = e.context.connection;
								bpmnId = parseInt(shape.businessObject.$attrs.bpmnId);
								if (bpmnId) self.update_connect_callback({ id: bpmnId, e: shape });
							}
						});
					});

					bpmnModeler.on('subprocess.clicked', e => {
						console.log('subprocess.clicked', e);
						var bpmnId = parseInt(e.element.di.bpmnElement.$attrs.bpmnId);
						self.open_subflow({
							id: bpmnId,
						});
					});
				}
			} catch (err) {
				console.error('could not import BPMN 2.0 diagram', err);
			}
		}

		self.$diagram = bpmnModeler;

		openDiagram(this.props.diagram);

		self.double_click_callback = function (cutenode) {
			if (cutenode.type.indexOf("Flow") > 0)
				self._onEditEdge({
					id: cutenode.id,
					e: cutenode.e
				});
			else
				self._onEditNode({
					id: cutenode.id,
					e: cutenode.e
				});
		};

		self.destruction_callback = function (cutenode) {
			if (cutenode.type === "shape.removed")
				self._onRemoveNode({
					id: cutenode.id
				});
			else
				self._onRemoveEdge({
					id: cutenode.id
				});
		};

		self.update_connect_callback = function (cutenode) {
			var fromid = parseInt(cutenode.e.source.di.bpmnElement.$attrs.bpmnId);
			var toid = parseInt(cutenode.e.target.di.bpmnElement.$attrs.bpmnId);
			if (fromid && toid) {
				self._onUpdateEdge({
					id: cutenode.id,
					source_id: fromid,
					dest_id: toid,
					e: cutenode.e,
				});
			}
		};

		self.new_element_callback = function (cutenode) {
			if (cutenode.type === "connection.added") {
				var exceptType = /.*(Task|Flow|Event|Gateway)$/;
				if (!exceptType.test(cutenode.e.source.type) || !exceptType.test(cutenode.e.target.type)) return;
				var fromid = parseInt(cutenode.e.source.di.bpmnElement.$attrs.bpmnId);
				var toid = parseInt(cutenode.e.target.di.bpmnElement.$attrs.bpmnId);
				if (fromid && toid) {
					self._onAddEdge({
						source_id: fromid,
						dest_id: toid,
						name: cutenode.name,
						e: cutenode.e,
					});
				};
			} else {
				self._addNode({
					e: cutenode.e,
					name: cutenode.name,
					is_start: cutenode.e.type === 'bpmn:StartEvent',
					is_stop: cutenode.e.type === 'bpmn:EndEvent',
				});
			}

		};

		// eslint-disable-next-line no-unused-vars
		self.edit_label_callback = function (cutenode) {
			self._onEditLabel({ id: cutenode.id, text: cutenode.label, e: cutenode.e, });
		};

		self.open_subflow = function (cutenode) {
			var self = this;
			this._rpc({
				model: self.props.resModel,
				method: 'subflow',
				args: [cutenode.id],
			}).then(function (action) {
				if (action.res_id) {
					self.action.doAction(action,{
						additionalContext: {
							active_id: action.res_id,
							active_model: action.res_model
						}});
				} else {
					self.dialog.add(WarningDialog, { title:"Must had defined model's workflow", message: "You can only load workflows that have been defined for the corresponding model, and only nodes of type task can attach sub-processes" });
				}
			});
		};
		//self.$el.parent.css("overflow","hidden");
	};

};

//DiagramPlusController.template = 'DiagramPlusView.buttons';
DiagramPlusController.props = {
    ...standardViewProps,
    Model: Function,
    modelParams: Object,
    archInfo: Object,
}
