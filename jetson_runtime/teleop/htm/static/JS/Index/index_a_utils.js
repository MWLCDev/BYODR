function isMobileDevice() {
	return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

var screen_utils = {
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

var network_utils = {
	getSSID: async function () {
		try {
			const response = await fetch('/run_get_SSID');
			const data = await response.text();
			return data;
		} catch (error) {
			console.error('Error fetching SSID:', error);
			return null; // Provide a fallback or handle the error as needed
		}
	},
};

// Define the sockets that will be used for communication
var socket_utils = {
	_init: function () {
		// noop.
	},
	create_socket: function (path, binary = true, reconnect = 100, assign = function (e) {}) {
		var ws_protocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
		var ws_url = ws_protocol + document.location.hostname + ':' + document.location.port + path;
		var ws = new WebSocket(ws_url);
		// console.log(ws) //list of websockets used
		if (binary) {
			ws.binaryType = 'arraybuffer';
		}
		assign(ws);
		var _assigned_on_close = ws.onclose;
		ws.onclose = function () {
			if (typeof ws.is_reconnect == 'function' && ws.is_reconnect()) {
				setTimeout(function () {
					socket_utils.create_socket(path, binary, reconnect, assign);
				}, reconnect);
			}
			if (typeof _assigned_on_close === 'function') {
				_assigned_on_close();
			}
		};
	},
};

var dev_tools = {
	_develop: null,
	_image_cache: new Map(),

	_random_choice: function (arr) {
		return arr[Math.floor(Math.random() * arr.length)];
	},

	_parse_develop: function () {
		const params = new URLSearchParams(window.location.search);
		var _develop = params.get('develop');
		if (_develop != undefined) {
			_develop = ['xga', 'svga', 'vga'].includes(_develop) ? _develop : 'xga';
		}
		return _develop;
	},

	_init: function () {
		this._develop = this._parse_develop();
	},

	is_develop: function () {
		return this._develop == undefined ? this._parse_develop() : this._develop;
	},

	get_img_dimensions: function () {
		const _key = this.is_develop();
		switch (_key) {
			case 'xga':
				return [1024, 768];
			case 'svga':
				return [800, 600];
			case 'vga':
				return [640, 480];
			default:
				return [320, 240];
		}
	},

	get_img_url: function (camera_position) {
		const _key = this.is_develop();
		return '/develop/img_' + camera_position + '_' + _key + '.jpg';
	},

	get_img_blob: async function (camera_position, callback) {
		const _url = this.get_img_url(camera_position);
		if (this._image_cache.has(_url)) {
			callback(this._image_cache.get(_url));
		} else {
			const response = await fetch(_url);
			const blob = await response.blob();
			this._image_cache.set(_url, blob);
			callback(blob);
			// console.log("Image cached " + _url);
		}
	},

	set_next_resolution: function () {
		var _next = null;
		const _key = this.is_develop();
		switch (_key) {
			case 'xga':
				_next = 'svga';
				break;
			case 'svga':
				_next = 'vga';
				break;
			case 'vga':
				_next = 'qvga';
				break;
			default:
				_next = 'xga';
		}
		this._develop = _next;
	},
};

var page_utils = {
	_capabilities: null,

	_init: function () {
		this.request_capabilities((capabilities) => {
			// console.log('Received platform vehicle ' + dev_tools._vehicle);
		});
	},

	request_capabilities: function (callback) {
		const _instance = this;
		// Check if capabilities are already loaded
		if (_instance._capabilities == undefined) {
			if (dev_tools.is_develop()) {
				// If in development mode, simulate capabilities
				_instance._capabilities = {
					platform: {
						vehicle: dev_tools._random_choice(['rover1', 'carla1']),
						video: { front: { ptz: 0 }, rear: { ptz: 0 } },
					},
				};
				callback(_instance._capabilities);
			} else {
				// Fetch real capabilities from server if not in develop mode
				jQuery.get('/teleop/system/capabilities', function (data) {
					_instance._capabilities = data;
					callback(_instance._capabilities);
				});
			}
		} else {
			// If already loaded, use the existing capabilities
			callback(_instance._capabilities);
		}
	},

	get_stream_type: function () {
		var stream_type = window.localStorage.getItem('video.stream.type');
		if (stream_type == 'h264') {
			return 'h264';
		} else {
			return 'mjpeg';
		}
	},

	set_stream_type: function (stream_type) {
		window.localStorage.setItem('video.stream.type', stream_type.toLowerCase());
	},
};
export { screen_utils, network_utils, socket_utils, dev_tools, page_utils, isMobileDevice };
