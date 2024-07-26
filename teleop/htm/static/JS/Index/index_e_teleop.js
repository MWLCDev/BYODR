import { screen_utils, teleop_screen } from './index_c_screen.js';
import { gamepad_controller } from './index_b_gamepad.js';
import { socket_utils } from './index_a_utils.js';
import CTRL_STAT from '../mobileController/mobileController_z_state.js'; // Stands for control state

class RealServerSocket {
	constructor() {
		this.server_message_listeners = [];
	}
	_notify_server_message_listeners(message) {
		this.server_message_listeners.forEach(function (cb) {
			cb(message);
		});
	}
	add_server_message_listener(cb) {
		this.server_message_listeners.push(cb);
	}
	_capture() {
		const _instance = this;
		const _socket = _instance.socket;
		if (_socket != undefined && _socket.readyState == 1) {
			_socket.send('{}');
		}
	}
	_start_socket() {
		const _instance = this;
		const _socket = _instance.socket;
		if (_socket == undefined) {
			socket_utils.create_socket('/ws/log', false, 250, function (ws) {
				_instance.socket = ws;
				ws.attempt_reconnect = true;
				ws.is_reconnect = function () {
					return ws.attempt_reconnect;
				};
				ws.onopen = function () {
					console.log('Server socket connection established.');
					_instance._capture();
				};
				ws.onclose = function () {
					console.log('Server socket connection closed.');
				};
				ws.onmessage = function (evt) {
					var message = JSON.parse(evt.data);
					// console.log(message);
					setTimeout(function () {
						_instance._capture();
					}, 40);
					setTimeout(function () {
						_instance._notify_server_message_listeners(screen_utils._decorate_server_message(message));
					}, 0);
				};
			});
		}
	}
	_stop_socket() {
		const _instance = this;
		const _socket = _instance.socket;
		if (_socket != undefined) {
			_socket.attempt_reconnect = false;
			if (_socket.readyState < 2) {
				_socket.close();
			}
			_instance.socket = null;
		}
	}
}

class MovementCommandSocket {
	constructor() {
		// noop.
		//
	}
	_send(command) {
		if (this.socket != undefined && this.socket.readyState == 1) {
			this.socket.send(JSON.stringify(command));
		}
	}

	_request_take_over_control() {
		var command = {};
		command._operator = 'force';
		this._send(command);
	}

	_capture(server_response) {
		const gc_active = gamepad_controller.is_active();
		const mc_active = CTRL_STAT.mobileIsActive;
		if (mc_active) {
			this._send(CTRL_STAT.throttleSteeringJson);
		} else {
			var gamepad_command = gc_active ? gamepad_controller.get_command() : {};
			// The selected camera for ptz control can also be undefined.
			gamepad_command.camera_id = -1;
			if (teleop_screen.selected_camera == 'front') {
				gamepad_command.camera_id = 0;
			} else if (teleop_screen.selected_camera == 'rear') {
				gamepad_command.camera_id = 1;
			}
			this._send(gamepad_command);
		}
		if (server_response != undefined && server_response.control == 'operator') {
			teleop_screen.controller_status = gc_active;
		} else if (server_response != undefined) {
			teleop_screen.controller_status = 2;
		}
		//E.g { steering - throttle - pan - tilt - camera_id}
		teleop_screen.controller_update(gamepad_command);
	}

	_start_socket() {
		const _instance = this;
		if (_instance.socket == undefined) {
			socket_utils.create_socket('/ws/ctl', false, 250, function (ws) {
				_instance.socket = ws;
				ws.attempt_reconnect = true;
				ws.is_reconnect = function () {
					return ws.attempt_reconnect;
				};
				ws.onopen = function () {
					// console.log("Operator socket connection was established.");
					teleop_screen.is_connection_ok = 1;
					_instance._capture();
				};
				ws.onclose = function () {
					teleop_screen.is_connection_ok = 0;
					teleop_screen.controller_update({});
					//console.log("Operator socket connection was closed.");
				};
				ws.onerror = function () {
					teleop_screen.controller_status = gamepad_controller.is_active();
					teleop_screen.is_connection_ok = 0;
					teleop_screen.controller_update({});
				};
				ws.onmessage = function (evt) {
					// console.log(evt)
					var message = JSON.parse(evt.data);
					setTimeout(function () {
						_instance._capture(message);
					}, 10000);
				};
			});
		}
	}

	_stop_socket() {
		const _instance = this;
		if (_instance.socket != undefined) {
			_instance.socket.attempt_reconnect = false;
			if (_instance.socket.readyState < 2) {
				_instance.socket.close();
			}
			_instance.socket = null;
		}
	}
}

export const server_socket = new RealServerSocket();
export const gamepad_socket = new MovementCommandSocket();

export function teleop_start_all() {
	gamepad_controller.reset();
	server_socket._start_socket();
	gamepad_socket._start_socket();
}

export function teleop_stop_all() {
	server_socket._stop_socket();
	// gamepad_socket._stop_socket(); // Because following will work with the mobile's screen closed
	gamepad_controller.reset();
}

server_socket.add_server_message_listener(function (message) {
	teleop_screen._server_message(message);
});
$('input#message_box_button_take_control').click(function () {
	gamepad_socket._request_take_over_control();
});
