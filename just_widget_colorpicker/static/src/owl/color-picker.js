/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
//import { CharField } from "@web/views/fields/char/char_field";

import { Component, onWillUpdateProps, useRef, onMounted, useState, useExternalListener } from "@odoo/owl";

export class FieldColorPicker extends Component {

	static template = "FieldColorPicker";
    static props = {
 		...standardFieldProps,
		border: { type: String, optional: true },
		value: { type: String, optional: true },
	};

    setup() {
	    useExternalListener(window, "resize", this.reCalculatePostion, { capture: true });
		this.button = useRef('justcolor');
		this.scope = useRef('justscope');
        this.$el = $(this.scope.el);
		this.position = 'under';
		this.isSupportNativeColorPicker = this.isSupportNativeColorPicker();
		this.props.value = this.props.record.data[this.props.name] || '#ff';
		this.state = useState({
			color: this.props.value || '#ff',
			commonColor: [
				[
					'#ffffff', '#000000', '#eeece1', '#1f497d', '#4f81bd',
					'#c0504d', '#9bbb59', '#8064a2', '#4bacc6', '#f79646'
				],
				[
					'#f2f2f2', '#808080', '#ddd8c2', '#c6d9f1', '#dbe5f1',
					'#f2dbdb', '#eaf1dd', '#e5dfec', '#daeef3', '#fde9d9'
				],
				[
					'#d9d9d9', '#595959', '#c4bc96', '#8db3e2', '#b8cce4',
					'#e5b8b7', '#d6e3bc', '#ccc0d9', '#b6dde8', '#fbd4b4'
				],
				[
					'#bfbfbf', '#404040', '#938953', '#548dd4', '#95b3d7',
					'#d99594', '#c2d69b', '#b2a1c7', '#92cddc', '#fabf8f'
				],
				[
					'#a6a6a6', '#262626', '#4a442a', '#17365d', '#365f91',
					'#943634', '#76923c', '#5f497a', '#31849b', '#e36c0a'
				],
				[
					'#7f7f7f', '#0d0d0d', '#1c1a10', '#0f243e', '#243f60',
					'#622423', '#4e6128', '#3f3151', '#205867', '#974706'
				]
			],
			standardColor: [
				'#c00000', '#ff0000', '#ffc000', '#ffff00', '#92d050',
				'#00b050', '#00b0f0', '#0070c0', '#002060', '#7030a0'
			],
			latestColor: this.getLatestColor(),

			// used in the previewer
			hoveredColor: this.props.value || '#ff',
			pickerInputId: (+new Date() * 1e6 + Math.floor(Math.random() * 1e6)).toString(36),
		});

        onMounted(() => {
			this.selectColor(this.props.value);
        });

		onWillUpdateProps((nextProps) => {
			this.state.color = nextProps.value || '#ff';
			this.state.latestColor = this.getLatestColor();
			this.props.record.update({ [this.props.name]: nextProps.value || '#ff' });
		});
	};

	get isReadonly() {
		return this.props.record.isReadonly(this.props.name);
	};

	reCalculatePostion() {
		var newPostion = this.getscopePosition(this.button.el);
		this.$el.css(newPostion);
	};


	isPickerEnable() {
		return this.props.readonly ? !this.props.readonly : true;
	};

	selectColor(color) {
		//$(this.scope.el).find('.colorpicker-preview').css('background-color', color);
		if (this.props.border)
			$(this.button.el).css('border-color', color);
		else
			$(this.button.el).css('background-color', color);

		this.props.value = color;

		this.hoveredColor = color;

		this.setLatestColor(color);
		this.latestColor = this.getLatestColor();
	};

	rgb2hex(item) {
		var rgb = $(item).css('background-color');
		rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
		if (rgb[3]) {
			function hex(x) {
				return ("0" + parseInt(x).toString(16)).slice(-2);
			}
			rgb = "#" + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
		}
		return rgb;
	};

	nativeColor(e) {
		var color = e.currentTarget.value;
		this.selectColor(color);
		this.closeColorPicker(e);
	};

	selectColorAndClose(e) {
		var color = $(e.target).css('background-color');
		//var color = this.rgb2hex(e.target);
		this.selectColor(color);
		this.closeColorPicker(e);
		//this.props.setDirty(true);
		this.props.record.update({ [this.props.name] : color });
        //this.props.record.save();
 	};

	previewColor(e) {
		var color = $(e.target).css('background-color');
		this.$el.find('.colorpicker-preview').css('background-color', color);
		this.hoveredColor = color;
	};

	closeColorPicker(e) {
		this.$el.css('display','none');
		this.$el.hide();
	};

	openColorPicker(e) {
		var enable = this.isPickerEnable();
        this.$el = $(this.scope.el);
		if (enable) {
			var templatePostion = this.getscopePosition(this.button.el);

			this.$el.css(templatePostion);
			this.$el.css('display','block');
			$(this.button.el).focus();
		}
	};

	keepPickerOpen(e) {
		e.stopPropagation();
	};

	getUIMemory() {
		var uiMemory = window.localStorage.getItem('ui-color-picker');

		if (!uiMemory) {
			return null;
		}

		try {
			uiMemory = JSON.parse(uiMemory)
		} catch (e) {
			return null;
		}

		return uiMemory;
	};

	getLatestColor() {
		var uiMemory = this.getUIMemory();

		return uiMemory ? uiMemory.latestColor : [];
	};

	setLatestColor(color) {
		var uiMemory = this.getUIMemory() || {};
		var latest = this.getLatestColor();


		if (latest && latest instanceof Array) {
			var idx = latest.indexOf(color);

			if (idx != -1) {
				latest.splice(idx, 1);
			}
			latest.unshift(color);

		} else {
			latest = [color];
		};

		if (latest.length > 10) {
			latest = latest.slice(0, 10);
		};

		uiMemory.latestColor = latest;

		window.localStorage.setItem('ui-color-picker', JSON.stringify(uiMemory));
	};

	// check for native support
	isSupportNativeColorPicker() {
		var i = document.createElement('input');
		i.setAttribute('type', 'color');

		return i.type !== 'text';
	};

	getOffset(elem, fixedPosition) {
        // odoo 16 the position is abslutly

		// var x = 0,
		// 	y = 0,
		// 	scrollX = 0,
		// 	scrollY = 0;
		// while (elem && !isNaN(elem.offsetLeft) && !isNaN(elem.offsetTop)) {
		// 	x += elem.offsetLeft;
		// 	y += elem.offsetTop;
		// 	if (!fixedPosition && elem.tagName === 'MAIN') {
		// 		scrollX += document.documentElement.scrollLeft || elem.scrollLeft;
		// 		scrollY += document.documentElement.scrollTop || elem.scrollTop;
		// 	} else {
		// 		scrollX += elem.scrollLeft;
		// 		scrollY += elem.scrollTop;
		// 	}
		// 	if (elem.className === 'modal-content o_form_view')
		// 		elem = null
		// 	else
		// 		elem = elem.offsetParent;
		// }
		return {
			top: elem.offsetTop,
			left: elem.offsetLeft,
			scrollX: elem.scrollLeft,
			scrollY: elem.scrollTop
		};
	};

	getscopePosition(element) {
		var
			positionValue,
			positionOffset = this.getOffset(element);

		if (this.position === 'top') {
			positionValue = {
				'top': positionOffset.top - 147,
				'left': positionOffset.left
			};
		} else if (this.position === 'under') {
			positionValue = {
				'top': positionOffset.top + 20,
				'left': positionOffset.left
			};
		} else if (this.position === 'over') {
			positionValue = {
				'top': positionOffset.top,
				'left': positionOffset.left
			};
		} else if (this.position === 'right') {
			positionValue = {
				'top': positionOffset.top,
				'left': positionOffset.left + 126
			};
		} else if (this.position === 'bottom') {
			positionValue = {
				'top': positionOffset.top + element[0].offsetHeight + 2,
				'left': positionOffset.left
			};
		} else if (this.position === 'left') {
			positionValue = {
				'top': positionOffset.top,
				'left': positionOffset.left - 150
			};
		}
		return {
			'top': positionValue.top + 'px',
			'left': positionValue.left + 'px'
		};
	};
};

export const fieldColorPicker = {
    component: FieldColorPicker,
    supportedTypes: ["char"],
    extractProps(fieldInfo, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
			border: fieldInfo.border,
        };
    },
};

registry.category("fields").add('justcolorpicker', fieldColorPicker);