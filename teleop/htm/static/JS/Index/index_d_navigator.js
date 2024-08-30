import { server_socket } from './index_e_teleop.js';

class RealNavigatorController {
  constructor() {
		const location = document.location;
		this.nav_path = location.protocol + '//' + location.hostname + ':' + location.port + '/ws/nav';
		this.random_id = Math.random(); // For browser control of navigation image urls.
		this.navigation_images = [null, null];
		this.routes = [];
		this.selected_route = null;
		this.started = false;
		this.backend_active = false;
		this.in_mouse_over = false;
		this.in_debug = false;
	}

	_server_message(message) {
		$('span#navigation_geo_lat').text(message.geo_lat.toFixed(6));
		$('span#navigation_geo_long').text(message.geo_long.toFixed(6));
		$('span#navigation_heading').text(message.geo_head_text);
		if (this.started) {
			if (message.inf_surprise != undefined) {
				const _nni_dist = Math.min(1, message.nav_distance[1]);
				$('span#navigation_match_image_distance').text(_nni_dist.toFixed(2));
				$('span#navigation_current_command').text(message.nav_command.toFixed(1));
				$('span#navigation_direction').text(message.nav_direction.toFixed(2));
				// Make the next expected navigation image stand out more as it comes closer.
				$('img#next_navigation_image').css('opacity', 1 - 0.85 * _nni_dist);
			}
			const backend_active = message.nav_active;
			this.backend_active = backend_active;
			this.navigation_images = message.nav_image;
			if (backend_active) {
				this.el_point.text(message.nav_point);
			}
		}
	}
}

const navigator_controller = new RealNavigatorController();

export function navigator_start_all() {
	navigator_controller.started = true;
}

export function navigator_stop_all() {
	navigator_controller.started = false;
}

// --------------------------------------------------- Initialisations follow --------------------------------------------------------- //
// prettier-ignore
server_socket.add_server_message_listener(function (message) {
    navigator_controller._server_message(message);
  });
