/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DiagramPlusController } from "./diagram_controller";
import { Model } from "@web/model/model";
import { _t } from "@web/core/l10n/translation";
import { FormArchParser } from "@web/views/form/form_arch_parser";

export const DiagramPlusView = {
    display_name: _t('DiagramPlus'),
    icon: 'fa-code-fork',
    multi_record: false,
    searchable: false,

    // Disable search
    withSearchPanel: false,
    withSearchBar: false,

    type: 'diagram_plus',
    viewType: 'diagram_plus',

    Controller: DiagramPlusController,
    Modle: Model,

    props: (props, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = props;
        const archInfo = new FormArchParser().parse(arch, relatedModels, resModel);

        this.nodes = arch.children[0];
        this.connectors = arch.children[1];
        this.node_model = this.nodes.attributes.object.value;
        this.connector_model = this.connectors.attributes.object.value;
        this.labels = $.map($.filter(arch.children, { tag: 'label' }),
            function (label) {
                return label.attributes.string.value;
            }
        );

        this.invisible_nodes = [];
        this.visible_nodes = [];
        this.node_fields_string = [];

        self = this;
        $.map(this.nodes.children, function (child) {
            var name = child.attributes.name.value;
            if (child.invisible === '1') {
                self.invisible_nodes.push(name);
            } else {
                var fieldString = props.fields[name].string ||
                    toTitleCase(name);
                self.visible_nodes.push(name);
                self.node_fields_string.push(fieldString);
            }
        });

        this.connector_fields_string = $.map(this.connectors.children,
            function (conn) {
                return props.fields[conn.attributes.name.value].string ||
                    toTitleCase(conn.attributes.name.value);
            }
        );

        var modelParams = {
            //currentId: this.params.currentId,
            nodes: this.nodes,
            labels: this.labels,
            invisible_nodes: this.invisible_nodes,
            visible_nodes: this.visible_nodes,
            node_fields_string: this.node_fields_string,
            node_model: this.node_model,
            connectors: this.connectors,
            connector_model: this.connector_model,
            connector_fields_string: this.connector_fields_string,
        };

        return {
            ...props,
            Model: Model,
            archInfo,
            modelParams,
        };
    },

    toTitleCase(str) {
        return str.replace(/\w\S*/g, function (txt) {
            return txt.charAt(0).toUpperCase() +
                txt.substr(1).toLowerCase();
        });
    },

    // controllerParams: $.extend({}, this.controllerParams, {
    //     domain: this.props.domain,
    //     context: this.props.context,
    //     ids: this.props.ids,
    //     //currentId: this.props.currentId,
    // }),

};

registry.category("views").add("diagram_plus", DiagramPlusView);
