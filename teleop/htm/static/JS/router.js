import { initializeSettings } from './userMenu/menu_settings.js';
import { fetchData } from './userMenu/menu_logbox.js';
import { setupMobileController, assignNavButtonActions } from './mobileController/mobileController_a_app.js';
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
	$('#' + selectedLinkId).addClass('active');
	window.localStorage.setItem('user.menu.screen', selectedLinkId); // Save the last visited screen in the cache
	const activeImageSrc = $('#' + selectedLinkId + ' img').attr('src'); // Get the src from the image of the active link
	$('.current_mode_img').attr('src', activeImageSrc); // Always update the mode image

	// Determine if mode switching is allowed on the current page
	if (['normal_ui_link', 'ai_training_link', 'autopilot_link', 'map_recognition_link', 'follow_link'].includes(selectedLinkId)) {
		ensureModePageLoaded(() => {
			updateMode(selectedLinkId);
		});
	} else {
		// Load settings page as before
		loadPageForSetting(selectedLinkId);
	}
}

function ensureModePageLoaded(callback) {
	const currentPage = $('main#application-content').data('current-page');
	const targetPage = isMobileDevice() ? '/mc' : '/normal_ui'; // Determine the target page based on device type

	// Check if current page supports mode switching
	if (currentPage === '/normal_ui' || currentPage === '/mc') {
		callback(); // Execute mode change if on the correct page
	} else {
		// Redirect to the appropriate mode page based on the device type
		$('main#application-content').load(targetPage, () => {
			$('main#application-content').data('current-page', targetPage);
			callback(); // Execute mode change after loading the correct page
		});
	}
}

function updateMode(selectedLinkId) {
	if (selectedLinkId === 'normal_ui_link') {
		loadContentBasedOnDevice();
	} else {
		$('.current_mode_img').attr('src', $('#' + selectedLinkId + ' img').attr('src'));
	}
}

function loadPageForSetting(selectedLinkId) {
	const urlMapping = {
		settings_link: ['/menu_settings', initializeSettings],
		controls_link: ['/menu_controls', null],
		events_link: ['/menu_logbox', fetchData],
	};
	if (selectedLinkId in urlMapping) {
		const [url, callback] = urlMapping[selectedLinkId];
		loadPage(url, callback);
	}
}

function loadPage(url, callback) {
	const container = $('main#application-content');
	container.empty();
	// AJAX call to get the .html page from tornado
	container.load(url, () => {
		callback ? callback() : undefined;
	});
	container.data('current-page', url); // Store current page
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

// Initialize event listeners on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function () {
  assignNavButtonActions()
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
