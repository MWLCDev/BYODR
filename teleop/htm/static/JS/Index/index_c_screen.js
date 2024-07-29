import { gamepad_controller } from './index_b_gamepad.js';
import { dev_tools, page_utils } from './index_a_utils.js';

export var screen_utils = {
	_version: '0.55.0',
	_arrow_images: {},
	_wheel_images: {},

	_create_image: function (url) {
		var img = new Image(); // Make sure to declare 'img' locally
		img.src = url;
		return img;
	},

	_init: function () {
		this._arrow_images.none = this._create_image('../static/assets/im_arrow_none.png?v=' + this._version);
		this._wheel_images.black = this._create_image('../static/assets/im_wheel_black.png?v=' + this._version);
		this._wheel_images.blue = this._create_image('../static/assets/im_wheel_blue.png?v=' + this._version);
		this._wheel_images.red = this._create_image('../static/assets/im_wheel_red.png?v=' + this._version);
	},

	_decorate_server_message: function (message) {
		message._is_on_autopilot = message.ctl == 5;
		message._has_passage = message.inf_total_penalty < 1;
		if (message.geo_head == undefined) {
			message.geo_head_text = 'n/a';
		} else {
			message.geo_head_text = message.geo_head.toFixed(2);
		}
		return message;
	},
};

var path_renderer = {
	_init: function () {
		const _instance = this;
	},

	_render_trapezoid: function (ctx, positions, fill) {
		ctx.lineWidth = 0.5;
		ctx.strokeStyle = 'rgb(255, 255, 255)';
		ctx.fillStyle = 'rgba(100, 217, 255, 0.3)';
		ctx.beginPath();
		ctx.moveTo(positions[0][0], positions[0][1]);
		ctx.lineTo(positions[1][0], positions[1][1]);
		ctx.lineTo(positions[2][0], positions[2][1]);
		ctx.lineTo(positions[3][0], positions[3][1]);
		ctx.closePath();
		ctx.stroke();
		ctx.fill();
	},

	_get_constants: function () {
		switch (dev_tools._vehicle) {
			case 'rover1':
				return [400 / 640, 120 / 480, 6 / 640, 8 / 480, 0.65, 0.65, 0.8, 0.7, 65 / 640, 2 / 480];
			default:
				return [400 / 640, 74 / 480, 6 / 640, 8 / 480, 0.65, 0.65, 0.8, 0.7, 80 / 640, 2 / 480];
		}
	},

	_render_path: function (ctx, path) {
		const canvas = ctx.canvas;
		const _constants = this._get_constants();
		const tz_width = _constants[0] * canvas.width;
		const tz_height = _constants[1] * canvas.height;
		const gap = _constants[2] * canvas.width;
		const cut = _constants[3] * canvas.height;
		const taper = _constants[4];
		const height_shrink = _constants[5];
		const gap_shrink = _constants[6];
		const cut_shrink = _constants[7];
		const w_steering = _constants[8] * canvas.width;
		const h_steering = _constants[9] * canvas.height;

		// Start from the middle of the base of the trapezoid.
		var a_x = canvas.width / 2 - tz_width / 2;
		var a_y = canvas.height - gap;
		var b_x = a_x + tz_width;
		var b_y = a_y;
		var idx = 0;

		path.forEach(function (element) {
			// Start in the lower left corner and draw counter clockwise.
			var w_base = b_x - a_x;
			var w_off = (w_base - w_base * taper) / 2;
			var v_height = tz_height * height_shrink ** idx;
			steer_dx = w_steering * element;
			steer_dy = h_steering * element;
			var c_x = b_x - w_off + steer_dx;
			var c_y = b_y - v_height + (element > 0 ? steer_dy : 0);
			var d_x = a_x + w_off + steer_dx;
			var d_y = a_y - v_height - (element < 0 ? steer_dy : 0);
			path_renderer._render_trapezoid(ctx, [
				[a_x, a_y],
				[b_x, b_y],
				[c_x, c_y],
				[d_x, d_y],
			]);
			// The next step starts from the top of the previous with gap.
			var c_shrink = 0.5 * cut * cut_shrink ** idx;
			var g_shrink = gap * gap_shrink ** idx;
			a_x = d_x + c_shrink;
			a_y = d_y - g_shrink;
			b_x = c_x - c_shrink;
			b_y = c_y - g_shrink;
			idx++;
		});
	},
};

export var teleop_screen = {
	el_viewport_container: null,
	el_drive_bar: null,
	el_drive_values: null,
	el_pilot_bar: null,
	el_message_box: null,
	overlay_center_markers: null,
	overlay_left_markers: null,
	overlay_right_markers: null,
	command_turn: null,
	command_ctl: null,
	server_message_listeners: [],
	in_debug: 0,
	is_connection_ok: 0,
	controller_status: 0,
	c_msg_connection_lost: 'Connection lost - please wait or refresh the page.',
	c_msg_controller_err: 'Controller not detected - please press a button on the device.',
	c_msg_teleop_view_only: 'Another user is in control - you can remain as viewer or take over.',
	active_camera: 'front', // The active camera is rendered on the main display.
	_debug_values_listeners: [],
	camera_activation_listeners: [],
	selected_camera: null, // Select a camera for ptz control.
	camera_selection_listeners: [],
	_camera_cycle_timer: null,
	_photo_snapshot_timer: null,
	_last_server_message: null,

	_init() {
		this.controller_status = gamepad_controller.is_active();
		this.el_viewport_container = $('div#viewport_container');
		this.el_drive_bar = $('div#debug_drive_bar');
		this.el_drive_values = $('div#debug_drive_values');
		this.el_pilot_bar = $('div#pilot_drive_values');
		this.el_message_box_container = $('div#message_box_container');
		this.el_message_box_message = this.el_message_box_container.find('div#message_box_message');
		this.el_button_take_control = this.el_message_box_container.find('input#message_box_button_take_control');
		this.overlay_center_markers = [$('div#overlay_center_distance0'), $('div#overlay_center_distance1')];
		this.overlay_left_markers = [$('div#overlay_left_marker0'), $('div#overlay_left_marker1')];
		this.overlay_right_markers = [$('div#overlay_right_marker0'), $('div#overlay_right_marker1')];
		this.add_camera_selection_listener(function () {
			teleop_screen._on_camera_selection();
		});
		this._select_camera('rear');
		this.toggle_debug_values(true);
		this.el_pilot_bar.click(function () {
			teleop_screen.toggle_debug_values();
		});
	},

	_render_distance_indicators: function () {
		const _show = this.active_camera == 'front';
		[this.overlay_center_markers, this.overlay_left_markers, this.overlay_right_markers].flat().forEach(function (_m) {
			if (_show) {
				_m.show();
			} else {
				_m.hide();
			}
		});
	},

	_select_next_camera: function () {
		// The active camera cannot be undefined.
		const _next = this.selected_camera == undefined ? this.active_camera : this.selected_camera == 'front' ? 'rear' : 'front';
		this._select_camera(_next);
	},

	_select_camera: function (name) {
		this.selected_camera = name;
		this.camera_selection_listeners.forEach(function (cb) {
			cb();
		});
	},

	_cycle_camera_selection: function (direction) {
		this._select_next_camera();
		if (this.selected_camera != undefined) {
			console.log('Camera ' + this.selected_camera + ' is selected for ptz control.');
		}
		this._camera_cycle_timer = null;
	},

	_schedule_camera_cycle: function (direction) {
		if (this._camera_cycle_timer == undefined) {
			this._camera_cycle_timer = setTimeout(function () {
				teleop_screen._cycle_camera_selection();
			}, 150);
		}
	},

	_schedule_photo_snapshot_effect: function () {
		if (this._photo_snapshot_timer != undefined) {
			clearTimeout(this._photo_snapshot_timer);
		}
		this._photo_snapshot_timer = setTimeout(function () {
			teleop_screen.el_viewport_container.fadeOut(50).fadeIn(50);
		}, 130);
	},

	_server_message: function (message) {
		this._last_server_message = message;
		// It may be the inference service is not (yet) available.
		const _debug = this.in_debug;
		if (message.inf_surprise != undefined) {
			$('span#inference_brake_critic').text(message.inf_brake_critic.toFixed(2));
			$('span#inference_obstacle').text(message.inf_brake.toFixed(2));
			$('span#inference_surprise').text(message.inf_surprise.toFixed(2));
			$('span#inference_critic').text(message.inf_critic.toFixed(2));
			$('span#inference_fps').text(message.inf_hz.toFixed(0));
			$('span#inference_desired_speed').text(message.des_speed.toFixed(1));
			// Calculate the color schemes.
			const red_brake = Math.min(255, message.inf_brake_penalty * 2 * 255);
			const green_brake = (1 - 2 * Math.max(0, message.inf_brake_penalty - 0.5)) * 255;
			$('span#inference_brake_critic').css('color', `rgb(${red_brake}, ${green_brake}, 0)`);
			$('span#inference_obstacle').css('color', `rgb(${red_brake}, ${green_brake}, 0)`);
			const red_steer = Math.min(255, message.inf_steer_penalty * 2 * 255);
			const green_steer = (1 - 2 * Math.max(0, message.inf_steer_penalty - 0.5)) * 255;
			$('span#inference_surprise').css('color', `rgb(${red_steer}, ${green_steer}, 0)`);
			$('span#inference_critic').css('color', `rgb(${red_steer}, ${green_steer}, 0)`);
		}
		// des_speed is the desired speed
		// vel_y is the actual vehicle speed
		var el_alpha_speed = $('p#alpha_speed_value');
		var el_alpha_speed_label = $('div#alpha_speed_label');
		var el_beta_speed_container = $('div#beta_speed');
		var el_beta_speed = $('p#beta_speed_value');
		if (message._is_on_autopilot) {
			el_alpha_speed.text(message.max_speed.toFixed(1));
			el_beta_speed.text(message.vel_y.toFixed(1));
		} else {
			el_alpha_speed.text(message.vel_y.toFixed(1));
		}
		var el_steering_wheel = $('img.steeringWheel');
		var el_autopilot_status = $('#autopilot_status');
		var str_command_ctl = message.ctl + '_' + message._has_passage;
		if (this.command_ctl != str_command_ctl) {
			this.command_ctl = str_command_ctl;
			if (message._is_on_autopilot) {
				el_alpha_speed_label.text('MAX');
				el_beta_speed_container.show();
			} else {
				el_alpha_speed_label.text('km/h');
				el_beta_speed_container.hide();
				el_autopilot_status.text('00:00:00');
				el_autopilot_status.css('color', 'white');
			}
			this._render_distance_indicators();
		}
		if (message._is_on_autopilot && message.ctl_activation > 0) {
			// Convert the time from milliseconds to seconds.
			const _diff = 1e-3 * message.ctl_activation;
			const _hours = Math.floor(_diff / 3600);
			const _mins = Math.floor((_diff - _hours * 3600) / 60);
			const _secs = Math.floor(_diff - _hours * 3600 - _mins * 60);
			const _zf_h = ('00' + _hours).slice(-2);
			const _zf_m = ('00' + _mins).slice(-2);
			const _zf_s = ('00' + _secs).slice(-2);
			el_autopilot_status.text(`${_zf_h}:${_zf_m}:${_zf_s}`);
			el_autopilot_status.css('color', 'rgb(100, 217, 255)');
		}
		var display_rotation = Math.floor(message.ste * 90.0);
		el_steering_wheel.css('transform', 'rotate(' + display_rotation + 'deg)');
	},

	_on_camera_selection: function () {
		const _active = this.active_camera;
		const _selected = this.selected_camera;
		const viewport_container = this.el_viewport_container;
		const overlay_image = $('img#overlay_image');

		viewport_container.removeClass('selected');
		overlay_image.removeClass('selected');
		if (_selected == _active) {
			viewport_container.addClass('selected');
		} else if (_selected != undefined) {
			overlay_image.addClass('selected');
		}
	},

	add_toggle_debug_values_listener: function (cb) {
		this._debug_values_listeners.push(cb);
	},

	toggle_debug_values: function (show) {
		if (show == undefined) {
			show = !this.in_debug;
		}
		if (show) {
			this.el_drive_bar.show();
			this.el_pilot_bar.css({ cursor: 'zoom-out' });
		} else {
			// this.el_drive_bar.hide();
			this.el_pilot_bar.css({ cursor: 'zoom-in' });
		}
		this.in_debug = show ? 1 : 0;
		this._render_distance_indicators();
		this._debug_values_listeners.forEach(function (cb) {
			cb(show);
		});
	},

	add_camera_activation_listener: function (cb) {
		this.camera_activation_listeners.push(cb);
	},

	add_camera_selection_listener: function (cb) {
		this.camera_selection_listeners.push(cb);
	},

	toggle_camera: function () {
		const name = this.active_camera == 'front' ? 'rear' : 'front';
		this.active_camera = name;
		this.selected_camera = null;
		this._render_distance_indicators();
		this.camera_activation_listeners.forEach(function (cb) {
			cb(name);
		});
		this.camera_selection_listeners.forEach(function (cb) {
			cb();
		});
	},
	//TODO: why it assigns the already init vars to consts?
	controller_update: function (command) {
		const message_box_container = this.el_message_box_container;
		const message_box_message = this.el_message_box_message;
		const button_take_control = this.el_button_take_control;
		const is_connection_ok = this.is_connection_ok;
		const controller_status = this.controller_status;
		const c_msg_connection_lost = this.c_msg_connection_lost;
		const c_msg_controller_err = this.c_msg_controller_err;
		const c_msg_teleop_view_only = this.c_msg_teleop_view_only;
		var show_message = false;
		var show_button = false;
		if (!is_connection_ok) {
			message_box_message.text(c_msg_connection_lost);
			message_box_message.removeClass();
			message_box_message.addClass('error_message');
			show_message = true;
		} else if (controller_status == 0) {
			message_box_message.text(c_msg_controller_err);
			message_box_message.removeClass();
			message_box_message.addClass('warning_message');
			show_message = true;
		} else if (controller_status == 2) {
			message_box_message.text(c_msg_teleop_view_only);
			message_box_message.removeClass();
			message_box_message.addClass('warning_message');
			show_message = true;
			show_button = true;
		}
		if (show_message) {
			if (show_button) {
				button_take_control.show();
			} else {
				button_take_control.hide();
			}
			message_box_container.show();
		} else {
			message_box_container.hide();
		}
		if (command != undefined && command.arrow_left) {
			this._schedule_camera_cycle();
		} else if (command != undefined && command.arrow_right) {
			this._schedule_camera_cycle();
		}
		if (command != undefined && command.button_right) {
			this._schedule_photo_snapshot_effect();
		}
	},

	on_canvas_init: function (width, height) {
		$('span#debug_screen_dimension').text(width + 'x' + height);
	},

	canvas_update: function (ctx) {
		const message = this._last_server_message;
		const _ap = message != undefined && message._is_on_autopilot;
		if (_ap && this.active_camera == 'front' && this.in_debug) {
			path_renderer._render_path(ctx, message.nav_path);
		}
	},
};

function screen_poll_platform() {
	if (dev_tools._vehicle == undefined) {
		setTimeout(function () {
			screen_poll_platform();
		}, 200);
	} else {
		teleop_screen._render_distance_indicators();
	}
}

// --------------------------------------------------- Initialisations follow --------------------------------------------------------- //
screen_utils._init();

if (page_utils.get_stream_type() == 'mjpeg') {
	$('#video_stream_mjpeg').addClass('active');
	$('#video_stream_h264').addClass('inactive');
} else {
	$('#video_stream_mjpeg').addClass('inactive');
	$('#video_stream_h264').addClass('active');
}
teleop_screen._init();
screen_poll_platform();
