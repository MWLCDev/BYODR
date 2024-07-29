import { initializeSettings } from './userMenu/menu_settings.js';
import { fetchData } from './userMenu/menu_logbox.js';
import { setupMobileController } from './mobileController/mobileController_a_app.js';
import { network_utils, page_utils, socket_utils, dev_tools } from './Index/index_a_utils.js';
import { screen_utils, teleop_screen } from './Index/index_c_screen.js';
import { gamepad_socket } from './Index/index_e_teleop.js';
import CTRL_STAT from './mobileController/mobileController_z_state.js'; // Stands for control state

function initializeAllNormalUIComponents() {
	teleop_screen._init();
	screen_utils._init();
	socket_utils._init();
	dev_tools._init();
	page_utils._init();

	if (page_utils.get_stream_type() == 'mjpeg') {
		$('#video_stream_type').val('mjpeg');
	} else {
		$('#video_stream_type').val('h264');
	}

	$('input#message_box_button_take_control').click(function () {
		gamepad_socket._request_take_over_control();
	});
}

function _user_menu_route_screen(screen) {
	$('.hamburger_menu_nav a').each(function () {
		$(this).removeClass('active');
	});

	// Use the main element directly
	const el_container = $('main#application-content');
	el_container.empty(); // Clear the existing content

	// Save the last visited screen in the cache
	window.localStorage.setItem('user.menu.screen', screen);
	CTRL_STAT.mobileIsActive = false;

	switch (screen) {
		case 'home_link':
			$('a#home_link').addClass('active');
			el_container.load('/normal_ui', initializeAllNormalUIComponents);
			break;
		case 'settings_link':
			$('a#settings_link').addClass('active');
			el_container.load('/menu_settings', initializeSettings); // Initialize settings after load
			break;
		case 'controls_link':
			$('a#controls_link').addClass('active');
			el_container.load('/menu_controls');
			break;
		case 'events_link':
			$('a#events_link').addClass('active');
			el_container.load('/menu_logbox', fetchData); // Fetch data after load
			break;
		case 'phone_controller_link':
			$('a#phone_controller_link').addClass('active');
			el_container.load('/mc', function () {
				setupMobileController();
				CTRL_STAT.mobileIsActive = true;
			});
			break;
	}
}

document.addEventListener('DOMContentLoaded', function () {
	// Set up the click handlers for menu navigation
	$('a#home_link, a#settings_link, a#controls_link, a#events_link, a#phone_controller_link').click(function () {
		_user_menu_route_screen(this.id);
	});
	network_utils
		.getSSID()
		.then((ssid) => {
			$('#header_bar #current_seg_name').text(ssid);
		})
		.catch((error) => {
			console.error('Failed to fetch SSID:', error);
		});
	// Load the last visited screen from cache or default to 'settings'
	var screen = window.localStorage.getItem('user.menu.screen') || 'settings_link';
	_user_menu_route_screen(screen);
});
