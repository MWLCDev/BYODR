import CTRL_STAT from '../mobileController/mobileController_z_state.js'; // Stands for control state

import { dev_tools, isMobileDevice, page_utils } from './index_a_utils.js';
import { gamepad_controller } from './index_b_gamepad.js';
import { gamepad_socket } from './index_e_teleop.js';

class DarkThemeManager {
	constructor() {
		this.darkModeCheckbox = document.querySelector('#nav_dark_mode_toggle_container input[type="checkbox"]');
		this.body = document.body;
		this.init();
	}

	init() {
		this.loadSavedState();
		this.addEventListeners();
	}

	loadSavedState() {
		const isDarkMode = localStorage.getItem('darkMode') === 'enabled';
		this.darkModeCheckbox.checked = isDarkMode;
		this.setTheme(isDarkMode);
	}

	addEventListeners() {
		this.darkModeCheckbox.addEventListener('change', () => this.toggleTheme());
	}

	toggleTheme() {
		const isDarkMode = this.darkModeCheckbox.checked;
		this.setTheme(isDarkMode);
		localStorage.setItem('darkMode', isDarkMode ? 'enabled' : 'disabled');
	}

	setTheme(isDarkMode) {
		this.body.classList.toggle('dark-mode', isDarkMode); //Add dark mode to body only
		this.updateLogo(isDarkMode);
	}

	updateLogo(isDarkMode) {
		const logo = document.querySelector('#header_bar #VOR_center_logo');
		const logoSrc = isDarkMode ? '../static/assets/VOR_Logo_light.png' : '../static/assets/VOR_Logo_dark.png';
		logo.setAttribute('src', logoSrc);
	}
}

class AdvancedThemeManager {
	constructor() {
		this.body = document.body;
		this.isAdvancedMode = true;
		this.loadAdvancedThemeSavedState();
		this.setAdvancedTheme();
	}

	bindActions() {
		this.advancedModeCheckBox = document.getElementById('pro-view-toggle-button');
		this.toggleStatus = $('#pro-view-toggle-status');
		this.addEventListeners();
		this.toggleAdvancedTheme();
	}

	loadAdvancedThemeSavedState() {
		const savedState = localStorage.getItem('advancedMode');
		this.isAdvancedMode = savedState === 'true';
	}

	addEventListeners() {
		this.advancedModeCheckBox.addEventListener('change', () => {
			this.isAdvancedMode = this.advancedModeCheckBox.checked;
			this.toggleAdvancedTheme();
		});
	}

	toggleAdvancedTheme() {
		this.changeToggleUI();
		this.setAdvancedTheme();
		localStorage.setItem('advancedMode', this.isAdvancedMode.toString());
	}

	changeToggleUI() {
		if (this.isAdvancedMode) {
			this.toggleStatus.text('on');
			this.advancedModeCheckBox.checked = true;
		} else {
			this.toggleStatus.text('off');
			this.advancedModeCheckBox.checked = false;
		}
		this.setAdvancedTheme();
	}

	setAdvancedTheme() {
		if (this.isAdvancedMode) {
			$('body').removeClass('advanced-mode');
		} else {
			$('body').addClass('advanced-mode');
		}
	}
}

class NavigationManager {
	constructor() {
		this.toggleBtn = document.getElementById('hamburger_menu_toggle');
		this.nav = document.querySelector('.hamburger_menu_nav');
		this.userMenu = document.getElementById('application_content');
		this.headerBar = document.getElementById('header_bar');
		this.navLinks = document.querySelectorAll('.hamburger_menu_nav a');

		this.setNavHeight(); // Set initial height
		this.addEventListeners();
	}

	addEventListeners() {
		this.toggleBtn.addEventListener('click', () => this.toggleSidebar());
		this.navLinks.forEach((link) => {
			link.addEventListener('click', () => this.toggleSidebar());
		});
		document.addEventListener('click', (event) => this.handleOutsideClick(event));
		window.addEventListener('resize', () => this.setNavHeight()); // Resize listener
	}

	setNavHeight() {
		this.nav.style.height = `${window.innerHeight}px`;
	}

	toggleSidebar() {
		this.nav.classList.toggle('active');
		this.toggleBtn.classList.toggle('active');
		this.userMenu.classList.toggle('expanded');
		this.headerBar.classList.toggle('expanded');
	}

	handleOutsideClick(event) {
		const isClickInsideNav = this.nav.contains(event.target);
		const isClickToggleBtn = this.toggleBtn.contains(event.target);
		if (!isClickInsideNav && !isClickToggleBtn && this.nav.classList.contains('active')) {
			this.toggleSidebar();
		}
	}
}

class HelpMessageManager {
	constructor() {
		this.help_message_img = $('.message_container img');
		this.help_message_grid = document.querySelector('.help_message_grid');
		this.manualModeMessages();
		$(document).mouseup((e) => {
			this.onClickOutside(e);
		});
	}

	manualModeMessages() {
		const messages = [
			'Drive forward: Press 14 slowly down',
			'Drive backwards: Press 1 slowly down',
			'Steering: Move 7 around',
			'Camera to drive position: Press 6',
			'Switch between cameras: Press 10 or 11',
			'Move selected camera around: Move 8 around',
			'Switch to autopilot mode: Press 3',
			'Capture the current frame with the front camera: Press 13',
			//TODO: see if more styles will be added
		];
		this.updateMessages(messages, true);
	}

	connectPhoneMessage() {
		const messages = ['1-open setting menu', '2- Add new wifi network', '3-Add username of the segment you see on the top', '4-In the password field, write the password that was sent in your email'];

		// First update the messages and then show the message container
		this.updateMessages(messages, false);
		this.showMessageContainer();
	}

	// Explicitly set application content state instead of toggling
	expandApplicationContent() {
		$('#application_content').addClass('expanded');
		$('#hamburger_menu_toggle').addClass('expanded');
		$('#header_bar').addClass('expanded');
	}

	collapseApplicationContent() {
		$('#application_content').removeClass('expanded');
		$('#hamburger_menu_toggle').removeClass('expanded');
		$('#header_bar').removeClass('expanded');
	}
	// Add a new method to ensure consistent handling of showing the container
	showMessageContainer() {
		const container = $('.message_container');
		container.removeClass('hidden').fadeIn(500);
		this.expandApplicationContent(); // Ensure the application content is expanded when showing
	}

	hideMessageContainer() {
		const container = $('.message_container');
		container.fadeOut(500, () => {
			container.addClass('hidden');
			this.collapseApplicationContent(); // Collapse content when the container is hidden
		});
	}

	// Private method to update the message grid
	updateMessages(messages, show_help_img) {
		if (show_help_img) {
			this.help_message_img.show();
		} else {
			this.help_message_img.hide();
		}
		this.help_message_grid.innerHTML = '';
		messages.forEach((msg) => {
			const p = document.createElement('p');
			p.className = 'message';
			p.textContent = msg;
			this.help_message_grid.appendChild(p);
		});
	}

	// Handle click outside the message container to close it
	onClickOutside(e) {
		var container = $('.message_container');
		if (container.is(':visible') && !container.is(e.target) && container.has(e.target).length === 0) {
			this.hideMessageContainer();
		}
	}
}

class MessageContainerManager {
	constructor(helpMessageManager) {
		this.helpMessageManager = helpMessageManager;
	}

	// Set up event handlers
	initEventHandlers() {
		try {
			$('.toggle_help_message').click(() => {
				this.helpMessageManager.manualModeMessages();
				this.toggleMessageContainer();
			});

			document.querySelector('.close_btn').addEventListener('click', () => {
				this.hideMessageContainer();
			});

			$(document).mouseup((e) => {
				this.onClickOutside(e);
			});
		} catch (error) {
			console.error('Error while init: ', error);
		}
	}

	// Toggle the visibility of the message container
	toggleMessageContainer() {
		$('.message_container').removeClass('hidden').hide().fadeIn(500);
		this.toggleApplicationContent();
	}

	// Hide the message container with a fade-out effect
	hideMessageContainer() {
		$('.message_container').fadeOut(500, () => {
			$('.message_container').addClass('hidden');
		});
		this.toggleApplicationContent();
	}

	// Toggle the application content and header bar expansion
	toggleApplicationContent() {
		$('#application_content').toggleClass('expanded');
		$('#hamburger_menu_toggle').toggleClass('expanded');
		$('#header_bar').toggleClass('expanded');
	}

	// Handle click outside the message container to close it
	onClickOutside(e) {
		var container = $('.message_container');
		if (container.is(':visible') && !container.is(e.target) && container.has(e.target).length === 0) {
			this.hideMessageContainer();
		}
	}
}

export function setupThemeManagers() {
	new NavigationManager();
	new DarkThemeManager();
	let advancedThemeManager = new AdvancedThemeManager();
	let helpMessageManager = new HelpMessageManager();
	let messageContainerManager = new MessageContainerManager(helpMessageManager);
	return { helpMessageManager, messageContainerManager, advancedThemeManager };
}

export var screen_utils = {
	_create_image: function (url) {
		var img = new Image(); // Make sure to declare 'img' locally
		img.src = url;
		return img;
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

class PathRenderer {
	// Method to render a trapezoid shape
	_renderTrapezoid(ctx, positions, fill = 'rgba(100, 217, 255, 0.3)') {
		if (!ctx || !positions || positions.length !== 4) {
			console.error('Invalid parameters passed to _renderTrapezoid');
			return;
		}

		ctx.lineWidth = 0.5;
		ctx.strokeStyle = 'rgb(255, 255, 255)';
		ctx.fillStyle = fill;
		ctx.beginPath();
		ctx.moveTo(positions[0][0], positions[0][1]);
		ctx.lineTo(positions[1][0], positions[1][1]);
		ctx.lineTo(positions[2][0], positions[2][1]);
		ctx.lineTo(positions[3][0], positions[3][1]);
		ctx.closePath();
		ctx.stroke();
		ctx.fill();
	}

	// Method to get constants based on the vehicle type
	_getConstants() {
		const constants = {
			default: [400 / 640, 74 / 480, 6 / 640, 8 / 480, 0.65, 0.65, 0.8, 0.7, 80 / 640, 2 / 480],
			rover1: [400 / 640, 120 / 480, 6 / 640, 8 / 480, 0.65, 0.65, 0.8, 0.7, 65 / 640, 2 / 480],
		};

		return constants[dev_tools._vehicle] || constants.default;
	}

	// Method to render the path
	renderPath(ctx, path) {
		if (!ctx || !path || !Array.isArray(path)) {
			console.error('Invalid parameters passed to renderPath');
			return;
		}

		const canvas = ctx.canvas;
		const [tzWidthFactor, tzHeightFactor, gapFactor, cutFactor, taper, heightShrink, gapShrink, cutShrink, wSteeringFactor, hSteeringFactor] = this._getConstants(); // Corrected the method call here

		// Calculating dimensions based on canvas size
		const tzWidth = tzWidthFactor * canvas.width;
		const tzHeight = tzHeightFactor * canvas.height;
		const gap = gapFactor * canvas.width;
		const cut = cutFactor * canvas.height;
		const wSteering = wSteeringFactor * canvas.width;
		const hSteering = hSteeringFactor * canvas.height;

		// Start from the middle of the base of the trapezoid.

		let baseAx = canvas.width / 2 - tzWidth / 2;
		let baseAy = canvas.height - gap;
		let baseBx = baseAx + tzWidth;
		let baseBy = baseAy;
		let idx = 0;

		path.forEach((steeringValue) => {
			// Calculate width of the base and offsets for the next step
			// Start in the lower left corner and draw counter clockwise.

			const baseWidth = baseBx - baseAx;
			const offsetWidth = (baseWidth - baseWidth * taper) / 2;
			const height = tzHeight * Math.pow(heightShrink, idx);
			const steerDx = wSteering * steeringValue;
			const steerDy = hSteering * steeringValue;

			// Calculate the coordinates for the trapezoid
			const cx = baseBx - offsetWidth + steerDx;
			const cy = baseBy - height + (steeringValue > 0 ? steerDy : 0);
			const dx = baseAx + offsetWidth + steerDx;
			const dy = baseAy - height - (steeringValue < 0 ? steerDy : 0);

			// Render the trapezoid
			this._renderTrapezoid(ctx, [
				[baseAx, baseAy],
				[baseBx, baseBy],
				[cx, cy],
				[dx, dy],
			]);

			// Update the base coordinates for the next step
			// The next step starts from the top of the previous with gap.

			const cutShrinked = 0.5 * cut * Math.pow(cutShrink, idx);
			const gapShrinked = gap * Math.pow(gapShrink, idx);

			baseAx = dx + cutShrinked;
			baseAy = dy - gapShrinked;
			baseBx = cx - cutShrinked;
			baseBy = cy - gapShrinked;

			idx++;
		});
	}
}

export var teleop_screen = {
	command_turn: null,
	command_ctl: null,
	server_message_listeners: [],
	in_debug: 0,
	is_connection_ok: 0,
	controller_status: 0,
	c_msg_connection_lost: 'Connection lost - please wait or refresh the page.',
	c_msg_controller_err: 'Controller not detected - please press a button on the device.',
	c_msg_teleop_view_only: 'Another user is in control - you can remain as viewer or take over.',
	c_msg_teleop_follow: 'Use your phone to activate the Following mode and stay nearby the robot.',
	c_msg_teleop_confidence_overview: 'Use your phone to activate the Following mode and stay nearby the robot.',
	active_camera: 'front', // The active camera is rendered on the main display.
	_debug_values_listeners: [],
	camera_activation_listeners: [],
	selected_camera: null, // Select a camera for ptz control.
	camera_selection_listeners: [],
	_camera_cycle_timer: null,
	_photo_snapshot_timer: null,
	_last_server_message: null,

	set_normal_ui_elements: function () {
		try {
			// Check each DOM element
			const elements = {
				viewport_container: $('div#viewport_container'),
				debug_drive_bar: $('div#debug_drive_bar'),
				debug_drive_values: $('div#debug_drive_values'),
				// pilot_drive_values: $('div#pilot_drive_values'),
				message_box_container: $('div#message_box_container'),
				overlay_image: $('img#mjpeg_camera_preview_image'),
				overlay_center_distance0: $('div#overlay_center_distance0'),
				overlay_center_distance1: $('div#overlay_center_distance1'),
				overlay_left_marker0: $('div#overlay_left_marker0'),
				overlay_left_marker1: $('div#overlay_left_marker1'),
				overlay_right_marker0: $('div#overlay_right_marker0'),
				overlay_right_marker1: $('div#overlay_right_marker1'),
			};

			// Check if each element exists
			for (const [name, element] of Object.entries(elements)) {
				if (element.length === 0) {
					console.error(`Element not found: ${name}`);
				}
			}

			// Assign elements to class properties
			this.el_viewport_container = elements['viewport_container'];
			this.el_drive_bar = elements['debug_drive_bar'];
			this.el_drive_values = elements['debug_drive_values'];
			// this.el_pilot_bar = elements['pilot_drive_values'];
			this.el_message_box_container = elements['message_box_container'];
			this.overlay_image = elements['overlay_image'];
			this.el_message_box_message = this.el_message_box_container.find('div#message_box_message');
			this.el_button_take_control = this.el_message_box_container.find('input#message_box_button_take_control');
			this.overlay_center_markers = [elements['overlay_center_distance0'], elements['overlay_center_distance1']];
			this.overlay_left_markers = [elements['overlay_left_marker0'], elements['overlay_left_marker1']];
			this.overlay_right_markers = [elements['overlay_right_marker0'], elements['overlay_right_marker1']];
		} catch (error) {
			console.error('Error in teleop_screen.set_normal_ui_elements():', error);
		}
	},

	_init() {
		try {
			this.path_renderer = new PathRenderer();

			//normal ui related
			this.controller_status = gamepad_controller.is_active();
			this.add_camera_selection_listener(function () {
				teleop_screen._on_camera_selection();
			});
			this._select_camera('rear');
			$('#video_stream_type').val(page_utils.get_stream_type() === 'mjpeg' ? 'mjpeg' : 'h264');
			$('#message_box_button_take_control').click(() => gamepad_socket._request_take_over_control());
		} catch (error) {
			console.error('Error in teleop_screen._init():', error);
		}
	},

	_render_distance_indicators: function () {
		const _show = this.active_camera == 'front';
		if (!isMobileDevice()) {
			[this.overlay_center_markers, this.overlay_left_markers, this.overlay_right_markers].flat().forEach(function (_m) {
				if (_show) {
					_m.show();
				} else {
					_m.hide();
				}
			});
		}
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
		var el_inf_speed = $('div.inf_speed');
		var el_inf_speed_val = $('p.inf_speed_value');
		var el_inf_speed_label = $('div.inf_speed_label');
		var el_rover_speed = $('p.rover_speed_value');
		var el_steering_wheel = $('img.steeringWheel');
		var el_autopilot_status = $('.autopilot_status');
		if (message._is_on_autopilot) {
			el_inf_speed.show();
			el_autopilot_status.show();
			el_inf_speed_val.text(message.max_speed.toFixed(1));
			el_inf_speed_label.text('MAX');
			this._render_distance_indicators();
			this.control_current_mode_btn_mc(true);
		} else {
			el_inf_speed.hide();
			el_autopilot_status.text('00:00:00');
			el_autopilot_status.hide();
			this.control_current_mode_btn_mc(false);
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
		el_rover_speed.text(message.vel_y.toFixed(1));
		if (message.vel_y >= 0) {
			var display_rotation = Math.floor(message.ste * 90.0);
			el_steering_wheel.css('transform', 'rotate(' + display_rotation + 'deg)');
		} else {
			var display_rotation = Math.floor(message.ste * -90.0 - 180);
			el_steering_wheel.css('transform', 'rotate(' + display_rotation + 'deg)');
		}
	},
	control_current_mode_btn_mc: function (active) {
		if (CTRL_STAT.currentPage == 'autopilot_link') {
			if (active) {
				$('#mobile_controller_container .current_mode_button').text('stop');
				$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
				$('#mobile_controller_container .current_mode_button').css('border', 'none');
			} else {
				$('#mobile_controller_container .current_mode_button').text('start');
				$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
				$('#mobile_controller_container .current_mode_button').css('color', 'white');
				$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
			}
		}
	},
	_on_camera_selection: function () {
		const _active = this.active_camera;
		const _selected = this.selected_camera;
		this.el_viewport_container.removeClass('selected');
		this.overlay_image.removeClass('selected');
		if (_selected == _active) {
			this.el_viewport_container.addClass('selected');
		} else if (_selected != undefined) {
			this.overlay_image.addClass('selected');
		}
	},

	add_toggle_debug_values_listener: function (cb) {
		this._debug_values_listeners.push(cb);
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

	message_box_update: function () {
		if (CTRL_STAT.currentPage == 'follow_link' && this.el_message_box_message != undefined) {
			this.el_message_box_message.text(this.c_msg_teleop_follow);
		} else if (CTRL_STAT.currentPage == 'map_recognition_link' && this.el_message_box_message != undefined) {
			this.el_message_box_message.text(this.c_msg_teleop_confidence_overview);
		}
	},

	//Why it assigns the already init vars to consts?
	controller_update: function (command) {
		try {
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
			if (message_box_message != undefined) {
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
			}
		} catch (error) {
			console.error('Error in controller_update: ', error);
		}
	},
	/**
	 * Used by the two stream quality classes (mjpeg and h264) to show the width of the stream on the debug (advanced) bar
	 */
	on_canvas_init: function (width, height) {
		$('span#debug_screen_dimension').text(width + 'x' + height);
	},

	/**
	 * check if on autopilot mode, if yes, then draw the trapezoid. Used by the two stream quality classes
	 */
	canvas_update: function (ctx) {
		try {
			const message = this._last_server_message;
			const _ap = message != undefined && message._is_on_autopilot;
			if (_ap && this.active_camera == 'front') {
				this.path_renderer.renderPath(ctx, message.nav_path);
			}
		} catch (error) {
			console.error('Error while rendering autopilot path: ', error);
		}
	},
};

export function screen_poll_platform() {
	if (dev_tools._vehicle == undefined) {
		setTimeout(function () {
			screen_poll_platform();
		}, 200);
	} else {
		teleop_screen._render_distance_indicators();
	}
}

screen_poll_platform();
