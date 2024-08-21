import { page_utils, socket_utils } from './index_a_utils.js';
import { teleop_screen } from './index_c_screen.js';

class MJPEGFrameController {
	constructor() {
		this._target_timeout = null;
		// larger = more smoothing
		this._time_smoothing = 0.8;
		this._actual_fps = 0;
		this._target_fps = 0;
		this._timeout = 0;
		this._duration = 1000;
		this._request_start = performance.now();
		this.max_jpeg_quality = 50;
		this.jpeg_quality = 20;
		this.min_jpeg_quality = 25;
		this.update_framerate();
	}
	set_target_fps(x) {
		this._actual_fps = x;
		this._target_fps = x;
		this._target_timeout = this._target_fps > 0 ? 1000 / this._target_fps : null;
	}
	get_actual_fps() {
		return this._actual_fps;
	}

	update_framerate() {
		try {
			if (this._target_timeout === undefined) {
				this._timeout = null;
			} else {
				const _now = performance.now();
				const _duration = _now - this._request_start;
				this._duration = this._time_smoothing * this._duration + (1 - this._time_smoothing) * _duration;
				this._request_start = _now;
				this._actual_fps = Math.round(1000.0 / this._duration);
				const q_step = Math.min(1, Math.max(-1, this._actual_fps - this._target_fps));
				this.jpeg_quality = Math.min(this.max_jpeg_quality, Math.max(this.min_jpeg_quality, this.jpeg_quality + q_step));
				this._timeout = Math.max(0, this._target_timeout - this._duration);
			}
			return this._timeout;
		} catch (error) {
			console.error('Error updating framerate:', error);
		}
	}
}

class MJPEGControlLocalStorage {
	constructor() {
		this.min_jpeg_quality = 25;
		this.max_jpeg_quality = 50;
		this.load();
	}
	set_max_quality(val) {
		try {
			if (val > 0 && val <= 100) {
				this.max_jpeg_quality = val;
				// Modify the minimum quality in lockstep with the maximum.
				var _min = val / 2.0;
				if (_min < 5) {
					_min = 5;
				}
				this.min_jpeg_quality = _min;
			}
		} catch (error) {
			console.error('Error setting maximum quality:', error);
		}
	}
	increase_quality() {
		this.set_max_quality(this.max_jpeg_quality + 5);
	}
	decrease_quality() {
		this.set_max_quality(this.max_jpeg_quality - 5);
	}
	load() {
		try {
			var _quality_max = window.localStorage.getItem('mjpeg.quality.max');
			if (_quality_max != null) {
				this.set_max_quality(JSON.parse(_quality_max));
			}
		} catch (error) {
			console.error('Error loading:', error);
		}
	}
	save() {
		window.localStorage.setItem('mjpeg.quality.max', JSON.stringify(this.max_jpeg_quality));
	}
}

class RealCameraController {
	constructor(camera_position, frame_controller, message_callback) {
		this.camera_position = camera_position;
		this.message_callback = message_callback;
		this.frame_controller = frame_controller;
		this._socket_capture_timer = null;
		this._socket_close_timer = null;
		this.socket = null;
	}
	_clear_socket_close_timer() {
		if (this._socket_close_timer != undefined) {
			clearTimeout(this._socket_close_timer);
		}
	}
	_clear_socket_capture_timer() {
		if (this._socket_capture_timer != undefined) {
			clearTimeout(this._socket_capture_timer);
		}
	}
	capture() {
		try {
			var _instance = this;
			_instance._clear_socket_close_timer();
			_instance._clear_socket_capture_timer();
			_instance._socket_close_timer = setTimeout(function () {
				if (_instance.socket != undefined) {
					_instance.socket.close(4001, 'Done waiting for the server to respond.');
				}
			}, 1000);
			// E.g. '{"camera": "front", "quality": 50, "display": "vga"}'
			if (_instance.socket != undefined && _instance.socket.readyState == 1) {
				_instance.socket.send(
					JSON.stringify({
						quality: _instance.frame_controller.jpeg_quality,
					})
				);
			}
		} catch (error) {
			console.error('Error capturing the frame:', error);
		}
	}
	set_rate(rate) {
		try {
			var _instance = this;
			switch (rate) {
				case 'fast':
					_instance.frame_controller.set_target_fps(16);
					_instance._socket_capture_timer = setTimeout(function () {
						_instance.capture();
					}, 0);
					break;
				case 'slow':
					_instance.frame_controller.set_target_fps(4);
					_instance._socket_capture_timer = setTimeout(function () {
						_instance.capture();
					}, 0);
					break;
				default:
					_instance.frame_controller.set_target_fps(0);
			}
		} catch (error) {
			console.error('Error setting the frame rate:', error);
		}
	}

	start_socket() {
		try {
			var _instance = this;
			var _cam_uri = '/ws/cam/' + _instance.camera_position;
			socket_utils.create_socket(_cam_uri, true, 250, function (ws) {
				_instance.socket = ws;
				ws.attempt_reconnect = true;
				ws.is_reconnect = function () {
					return ws.attempt_reconnect;
				};
				ws.onopen = function () {
					// console.log('MJPEG ' + _instance.camera_position + ' camera connection established.');
					//_instance.capture();
				};
				ws.onclose = function () {
					//console.log("MJPEG " + _instance.camera_position + " camera connection closed.");
				};
				ws.onmessage = function (evt) {
					_instance._clear_socket_close_timer();
					const _timeout = _instance.frame_controller.update_framerate();
					if (_timeout != undefined && _timeout >= 0) {
						_instance._socket_capture_timer = setTimeout(function () {
							_instance.capture();
						}, _timeout);
					}
					setTimeout(function () {
						var cmd = null;
						if (typeof evt.data == 'string') {
							cmd = evt.data;
						} else {
							cmd = new Blob([new Uint8Array(evt.data)], { type: 'image/jpeg' });
						}
						_instance.message_callback(cmd);
					}, 0);
				};
			});
		} catch (error) {
			console.error(`error while opening ${_instance.camera_position} socket: `, error);
		}
	}

	stop_socket() {
		try {
			if (this.socket != undefined) {
				this.socket.attempt_reconnect = false;
				if (this.socket.readyState < 2) {
					try {
						this.socket.close();
					} catch (err) {}
				}
			}
			this.socket = null;
		} catch (error) {
			console.error('Error trying to stop the socket:', error);
		}
	}
}

// One for each camera.
var front_camera_frame_controller = new MJPEGFrameController();
var rear_camera_frame_controller = new MJPEGFrameController();
var mjpeg_rear_camera;
var mjpeg_front_camera;

// Accessed outside of this module.
var mjpeg_page_controller = {
	store: new MJPEGControlLocalStorage(),
	camera_init_listeners: [],
	camera_image_listeners: [],
	el_preview_image: null,
	expand_camera_icon: null,

	init: function (cameras) {
		try {
			this.cameras = cameras;
			this.apply_limits();
			this.refresh_page_values();
			this.el_preview_image = $('img#mjpeg_camera_preview_image');
			this.expand_camera_icon = $('img#expand_camera_icon');
			this.expand_camera_icon.css({ cursor: 'zoom-in' });
			this.set_camera_framerates(teleop_screen.active_camera);
			this.bind_dom_actions();
			// Set the image receiver handlers.
			this.add_camera_listener(
				function (position, _cmd) {},
				function (position, _blob) {
					// Show the other camera in preview.
					if (position != teleop_screen.active_camera) {
						mjpeg_page_controller.el_preview_image.attr('src', _blob);
					}
				}
			);
		} catch (error) {
			console.error('Error while init camera:', error);
		}
	},

	bind_dom_actions: function () {
		try {
			$('#caret_down').click(function () {
				mjpeg_page_controller.decrease_quality();
				mjpeg_page_controller.refresh_page_values();
			});
			$('#caret_up').click(function () {
				mjpeg_page_controller.increase_quality();
				mjpeg_page_controller.refresh_page_values();
			});
			this.el_preview_image.click(function () {
				teleop_screen.toggle_camera();
			});
			this.expand_camera_icon.click(function () {
				const _instance = mjpeg_page_controller;
				const _state = _instance.el_preview_image.width() < 480 ? 'small' : 'medium';
				switch (_state) {
					case 'small':
						_instance.el_preview_image.width(480);
						_instance.el_preview_image.height(320);
						_instance.el_preview_image.css({ opacity: 0.5 });
						_instance.expand_camera_icon.css({ cursor: 'zoom-out' });
						break;
					default:
						_instance.el_preview_image.width(320);
						_instance.el_preview_image.height(240);
						_instance.el_preview_image.css({ opacity: 1 });
						_instance.expand_camera_icon.css({ cursor: 'zoom-in' });
				}
				// Reset the framerate.
				_instance.set_camera_framerates(teleop_screen.active_camera);
			});
		} catch (error) {
			console.error('Error while binding actions:', error);
		}
	},

	refresh_page_values: function () {
		$('span#mjpeg_quality_val').text(this.get_max_quality());
	},
	add_camera_listener: function (cb_init, cb_image) {
		this.camera_init_listeners.push(cb_init);
		this.camera_image_listeners.push(cb_image);
	},
	notify_camera_init_listeners: function (camera_position, _cmd) {
		this.camera_init_listeners.forEach(function (cb) {
			cb(camera_position, _cmd);
		});
	},
	notify_camera_image_listeners: function (camera_position, _blob) {
		this.camera_image_listeners.forEach(function (cb) {
			cb(camera_position, _blob);
		});
	},
	apply_limits: function () {
		var _instance = this;
		this.cameras.forEach(function (cam) {
			cam.frame_controller.max_jpeg_quality = _instance.get_max_quality();
			cam.frame_controller.min_jpeg_quality = _instance.get_min_quality();
		});
	},
	get_max_quality: function () {
		return this.store.max_jpeg_quality;
	},
	get_min_quality: function () {
		return this.store.min_jpeg_quality;
	},
	increase_quality: function () {
		this.store.increase_quality();
		this.apply_limits();
		this.store.save();
	},
	decrease_quality: function () {
		this.store.decrease_quality();
		this.apply_limits();
		this.store.save();
	},
	set_camera_framerates: function (position) {
		try {
			// The camera rates depend on visibility on the main screen and on the overlay div.
			const _mjpeg = page_utils.get_stream_type() == 'mjpeg';
			const _front_camera = this.cameras[0];
			const _rear_camera = this.cameras[1];
			if (_mjpeg) {
				_front_camera.set_rate(position == 'front' ? 'fast' : 'slow');
				_rear_camera.set_rate(position == 'rear' ? 'fast' : 'slow');
			} else {
				_front_camera.set_rate(position == 'front' ? 'off' : 'slow');
				_rear_camera.set_rate(position == 'rear' ? 'off' : 'slow');
			}
		} catch (error) {
			console.error('Error setting camera frame rate:', error);
		}
	},
};

// Setup both the camera socket consumers.
var mjpeg_rear_camera_consumer = function (_blob) {
	try {
		if (typeof _blob == 'string') {
			mjpeg_page_controller.notify_camera_init_listeners(mjpeg_rear_camera.camera_position, JSON.parse(_blob));
		} else {
			mjpeg_page_controller.notify_camera_image_listeners(mjpeg_rear_camera.camera_position, URL.createObjectURL(_blob));
			$('span#rear_camera_framerate').text(rear_camera_frame_controller.get_actual_fps().toFixed(0));
		}
	} catch (error) {
		console.error('Error setting rear camera consumer:', error);
	}
};

var mjpeg_front_camera_consumer = function (_blob) {
	try {
		if (typeof _blob == 'string') {
			mjpeg_page_controller.notify_camera_init_listeners(mjpeg_front_camera.camera_position, JSON.parse(_blob));
		} else {
			mjpeg_page_controller.notify_camera_image_listeners(mjpeg_front_camera.camera_position, URL.createObjectURL(_blob));
			$('span#front_camera_framerate').text(front_camera_frame_controller.get_actual_fps().toFixed(0));
		}
	} catch (error) {
		console.error('Error setting front camera consumer:', error);
	}
};

export function mjpeg_start_all() {
	if (mjpeg_rear_camera != undefined) {
		mjpeg_rear_camera.start_socket();
	}
	if (mjpeg_front_camera != undefined) {
		mjpeg_front_camera.start_socket();
	}
}

export function mjpeg_stop_all() {
	if (mjpeg_rear_camera != undefined) {
		mjpeg_rear_camera.stop_socket();
	}
	if (mjpeg_front_camera != undefined) {
		mjpeg_front_camera.stop_socket();
	}
}

function initMJPEGController() {
	mjpeg_page_controller.init([mjpeg_front_camera, mjpeg_rear_camera]);
}

function setupStreamTypeSelector() {
	$('#video_stream_type').change(function () {
		var selectedStreamType = $(this).val();
		page_utils.set_stream_type(selectedStreamType);
		location.reload();
	});
}

function setupCameraActivationListener() {
	// Set the socket desired fps when the active camera changes.
	teleop_screen.add_camera_activation_listener(function (position) {
		setTimeout(function () {
			mjpeg_page_controller.set_camera_framerates(position);
		}, 100);
	});
}

function setupMJPEGCanvasRendering(canvas) {
	if (page_utils.get_stream_type() !== 'mjpeg') return;
	// Render images for the active camera.
	const display_ctx = canvas.getContext('2d');
	mjpeg_page_controller.add_camera_listener(
		function (position, _cmd) {
			if (teleop_screen.active_camera == position && _cmd.action == 'init') {
				canvas.width = _cmd.width;
				canvas.height = _cmd.height;
				teleop_screen.on_canvas_init(_cmd.width, _cmd.height);
			}
		},
		function (position, _blob) {
			if (teleop_screen.active_camera == position) {
				const img = new Image();
				img.onload = function () {
					requestAnimationFrame(() => {
						// Do not run the canvas draws in parallel.
						display_ctx.drawImage(img, 0, 0);
						teleop_screen.canvas_update(display_ctx);
					});
				};
				// Set the src to trigger the image load.
				img.src = _blob;
			}
		}
	);
}

function initializeApplication(canvas) {
	try {
		initMJPEGController();
		setupStreamTypeSelector();
		setupCameraActivationListener();
		setupMJPEGCanvasRendering(canvas);
	} catch (error) {
		console.error('Error init MJPEG:', error);
	}
}

function findCanvasAndExecute() {
	const canvas = document.getElementById('viewport_canvas');
	if (canvas) {
		initializeApplication(canvas);
	} else {
		setTimeout(findCanvasAndExecute, 500);
	}
}

export function init_mjpeg() {
	mjpeg_rear_camera = new RealCameraController('rear', rear_camera_frame_controller, mjpeg_rear_camera_consumer);
	mjpeg_front_camera = new RealCameraController('front', front_camera_frame_controller, mjpeg_front_camera_consumer);
	findCanvasAndExecute();
}
