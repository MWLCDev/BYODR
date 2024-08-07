import { initializeSettings } from './userMenu/menu_settings.js';
import { LogBox } from './userMenu/menu_logbox.js';
import { setupMobileController, assignNavButtonActions } from './mobileController/mobileController_a_app.js';
import { isMobileDevice, network_utils, page_utils, socket_utils, dev_tools } from './Index/index_a_utils.js';
import { teleop_screen } from './Index/index_c_screen.js';
import { gamepad_socket } from './Index/index_e_teleop.js';
import { updateRelayStates } from './userMenu/menu_controls.js';
import CTRL_STAT from './mobileController/mobileController_z_state.js';

const initComponents = () => {
	try {
		[teleop_screen, socket_utils, dev_tools, page_utils].forEach((component) => component._init());
		$('#video_stream_type').val(page_utils.get_stream_type() === 'mjpeg' ? 'mjpeg' : 'h264');
		$('input#message_box_button_take_control').click(() => gamepad_socket._request_take_over_control());
	} catch (error) {
		console.log('error while init components', error);
	}
};
/**
 * Updates the visibility of header bar sections based on device type.
 */
const updateHeaderBar = () => {
	const sections = ['left_section', 'right_section'];
	sections.forEach((section) => $(`#header_bar .${section}`)[isMobileDevice() ? 'show' : 'hide']());
};

/**
 * Loads a page into the main content area and executes a callback if provided.
 * @param {string} url - The URL of the page to load.
 * @param {Function} [callback] - Optional callback to execute after loading the page.
 */
const loadPage = (url, callback) => {
	const container = $('main#application-content');
	container.empty().load(url, callback).data('current-page', url);
};

const updateModeUI = (selectedLinkId) => {
	$('.hamburger_menu_nav a').removeClass('active');
	$(`#${selectedLinkId}`).addClass('active');
	const activeImageSrc = $(`#${selectedLinkId} img`).attr('src');
	$('.current_mode_img').attr('src', activeImageSrc);
};

const handleUserMenuRoute = (selectedLinkId) => {
	CTRL_STAT.mobileIsActive = false;
	updateModeUI(selectedLinkId);

	CTRL_STAT.currentPage = selectedLinkId;
	localStorage.setItem('user.menu.screen', selectedLinkId);

	const modeSwitchingPages = ['normal_ui_link', 'ai_training_link', 'autopilot_link', 'map_recognition_link', 'follow_link'];
	if (modeSwitchingPages.includes(selectedLinkId)) {
		const targetPage = isMobileDevice() ? '/mc' : '/normal_ui';
		const currentPage = $('main#application-content').data('current-page');

		if (currentPage === '/normal_ui' || currentPage === '/mc') {
			selectedLinkId === 'normal_ui_link' ? loadContentBasedOnDevice() : null;
		} else {
			loadPage(targetPage, () => (selectedLinkId === 'normal_ui_link' ? loadContentBasedOnDevice() : null));
		}
	} else {
		const pageMap = {
			settings_link: ['/menu_settings', initializeSettings],
			controls_link: ['/menu_controls', updateRelayStates],
			events_link: [
				'/menu_logbox',
				() => {
					LogBox;
					LogBox.init();
				},
			],
		};
		const [url, callback] = pageMap[selectedLinkId] || [];
		url && loadPage(url, callback);
	}
};

const loadContentBasedOnDevice = () => {
	const url = isMobileDevice() ? '/mc' : '/normal_ui';
	loadPage(url, () => {
		initComponents();
		isMobileDevice() && setupMobileController();
		CTRL_STAT.mobileIsActive = isMobileDevice();
	});
};

document.addEventListener('DOMContentLoaded', () => {
	['events_link', 'phone_controller_link'].forEach((id) => $(`#${id}`)[isMobileDevice() ? 'hide' : 'show']());
	$('.hamburger_menu_nav a').on('click', function () {
		handleUserMenuRoute(this.id);
		assignNavButtonActions(this.id);
	});

	network_utils
		.getSSID()
		.then((ssid) => $('#header_bar #current_seg_name').text(ssid))
		.catch((error) => console.error('Failed to fetch SSID:', error));

	updateHeaderBar();
	handleUserMenuRoute(localStorage.getItem('user.menu.screen') || 'settings_link');
});
