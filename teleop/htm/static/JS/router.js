import { initializeSettings } from './userMenu/menu_settings.js';
import { fetchData } from './userMenu/menu_logbox.js';
import { setupMobileController } from './mobileController/mobileController_a_app.js';
import { isMobileDevice, network_utils, page_utils, socket_utils, dev_tools } from './Index/index_a_utils.js';
import { screen_utils, teleop_screen } from './Index/index_c_screen.js';
import { gamepad_socket } from './Index/index_e_teleop.js';
import CTRL_STAT from './mobileController/mobileController_z_state.js'; // Stands for control state

function initializeAllNormalUIComponents() {
	if (isMobileDevice()) {
		$('#header_bar .left_section').show();
		$('#header_bar .right_section').show();
		$('.current_mode_img').show();
	} else {
		$('#header_bar .left_section').hide();
		$('#header_bar .right_section').hide();
		$('.current_mode_img').show();
	}
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

function handleUserMenuRoute(selectedLinkId) {
	CTRL_STAT.mobileIsActive = false;
	$('.hamburger_menu_nav a').removeClass('active');
	console.log(selectedLinkId);
	$('#' + selectedLinkId).addClass('active');
	window.localStorage.setItem('user.menu.screen', selectedLinkId); // Save the last visited screen in the cache
	const activeImageSrc = $('#' + selectedLinkId + ' img').attr('src'); // Get the src from the image of the active link
	$('.current_mode_img').attr('src', activeImageSrc); // Always update the mode image

	if (selectedLinkId === 'home_link') {
		loadContentBasedOnDevice();
	} else if (selectedLinkId === 'settings_link') {
		loadPage('/menu_settings', initializeSettings);
	} else if (selectedLinkId === 'controls_link') {
		loadPage('/menu_controls');
	} else if (selectedLinkId === 'events_link') {
		loadPage('/menu_logbox', fetchData);
	} else if (selectedLinkId === 'phone_controller_link') {
		CTRL_STAT.mobileIsActive = true;
		// Consider if you need special handling here similar to 'home_link'
	}
}

function loadContentBasedOnDevice() {
	const container = $('main#application-content');
	if (!isMobileDevice()) {
		container.load('/normal_ui', () => {
			initializeAllNormalUIComponents();
		});
	} else {
		container.load('/mc', () => {
			setupMobileController();
			initializeAllNormalUIComponents();
			CTRL_STAT.mobileIsActive = true;
		});
	}
}

function loadPage(url, callback) {
	const container = $('main#application-content');
	container.empty(); // Clear the existing content only when loading new pages
	container.load(url, callback); // AJAX call to load the page
}

// Initialize event listeners on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function () {
	if (isMobileDevice()) {
		$('#events_link, #phone_controller_link').hide();
	} else {
		$('#events_link, #phone_controller_link').show();
	}

	$('.hamburger_menu_nav a').on('click', function () {
		handleUserMenuRoute(this.id);
	});

	network_utils
		.getSSID()
		.then((ssid) => {
			$('#header_bar #current_seg_name').text(ssid);
		})
		.catch((error) => {
			console.error('Failed to fetch SSID:', error);
		});

	// Ensure lastVisitedScreen is read correctly from localStorage or falls back to 'settings_link'
	const lastVisitedScreen = window.localStorage.getItem('user.menu.screen') || 'settings_link';
	handleUserMenuRoute(lastVisitedScreen);
});
