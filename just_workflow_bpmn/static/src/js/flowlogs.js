/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
//import { CharField } from "@web/views/fields/char/char_field";
import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";

import { useService } from "@web/core/utils/hooks";
import { Component, onWillUpdateProps, useRef, onMounted, useState, useExternalListener } from "@odoo/owl";
const { DateTime, Settings } = luxon;
import { formatDuration } from "@web/core/l10n/dates";
import { viewService } from "@web/views/view_service";
import { patch } from "@web/core/utils/patch";

export class showLogs extends Component {
	setup() {
		this.rpc = useService("rpc");
		this.state = useState({
			logs: this.props.value || '#ff',
		});

		onMounted(() => {
			this.start();
		});

		onWillUpdateProps((nextProps) => {
		});
	};

	start() {
		self = this;
		this.state.logs = null;
		this.props.record.context.active_test = false;
		self.rpc("/web/dataset/call_kw/log.workflow.trans/search_read",
			{
				model: 'log.workflow.trans',
				method: 'search_read',
				args: [],
				kwargs: {
					domain: [['model', '=', this.props.record.context.active_model],
					['res_id', '=', this.props.record.context.active_id]],
					fields: ["id", "create_uid", "create_date", "note"],
					context: this.props.record.context,
				}
			}
		).then((fields) => {
			this.props.logs = fields;
			$.map(this.props.logs, function (log) {
				log.avatar = self.getAvatarSource(log.create_uid[0]);
				log.username = log.create_uid[1];
				log.dateFromNow = self._computeDateFromNow(log.create_date);
				log.dateDay = self._computeDateDay(log.create_date);
			});

			var html = renderToString("just_workflow_engine.showlogs", { logs: this.props.logs });
			$(".o_ThreadView_core").html(html);
			//self.$(".o_FormRenderer_chatterContainer").show();
		});
	};

	/**
	 * @returns {string}
	 */
	_computeDateDay(date) {
		if (!date) {
			// Without a date, we assume that it's a today message. This is
			// mainly done to avoid flicker inside the UI.
			return _t("Today");
		}
		const datestr = DateTime.fromSQL(date);
		if (datestr.hasSame(DateTime.now(), "day")) {
			return _t("Today");
		} else if (datestr.hasSame(DateTime.local().minus({ days: 1 }), "day")) {
			return _t("Yesterday");
		}
		return datestr.toLocaleString(DateTime.DATE_FULL);
	};

	/**
	 * @returns {string}
	 */
	_computeDateFromNow(date) {
		const datestr = DateTime.fromSQL(date);
		var difftime = Math.floor(DateTime.now().diff(datestr, 'seconds') / 1000);
		if (difftime < 45) {
			return _t("now");
		} else if (difftime < 1800) {
			return formatDuration(difftime, true);
		}
		return datestr.toLocaleString(DateTime.DATETIME_FULL);
	};

	/**          
	 * Get the relative url of the avatar to display next to the message
	 *
	 * @override
			 * @return {string}
	  */
	getAvatarSource(userId) {
		if (userId) {
			var source = '/web/image?model=res.users&field=avatar_128&id=' + userId;
		} else {
			var source = '/mail/static/src/img/smiley/avatar.jpg';
		}
		return source;
	};
};

showLogs.template = "just_workflow_engine.flowlogs";
showLogs.description = "workflow logs show";

showLogs.props = {
	...standardFieldProps,
	Title: { type: String, optional: true },
};
showLogs.extractProps = ({ attrs }) => {
	return {
		Title: attrs.title,
	};
};

export const ShowLogs = {
	component: showLogs,
};

registry.category("fields").add("flowLogs", ShowLogs);