import { initializeSettings } from './userMenu/menu_settings.js';
import { fetchData } from './userMenu/menu_logbox.js';
import { start_all_handlers } from './index.js';
import { setupMobileController } from './mobileController/mobileController_a_app.js';
import { network_utils } from './Index/index_a_utils.js';

function _user_menu_route_screen(screen) {
	$('.hamburger_menu_nav a').each(function () {
		$(this).removeClass('active');
	});

	// Use the main element directly
	const el_container = $('main#application-content');
	el_container.empty(); // Clear the existing content

	// Save the last visited screen in the cache
	window.localStorage.setItem('user.menu.screen', screen);

	switch (screen) {
		case 'home_link':
			$('a#home_link').addClass('active');
			el_container.load('/normal_ui', function () {
				start_all_handlers();
			});
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
				console.log('should load the function');
				setupMobileController();
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
