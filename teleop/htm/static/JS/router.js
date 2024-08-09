import { initComponents, showHelp } from './index.js';
import { isMobileDevice } from './Index/index_a_utils.js';
import { setupMobileController } from './mobileController/mobileController_a_app.js';
import CTRL_STAT from './mobileController/mobileController_z_state.js'; // Stands for control state
import { initDomElem } from './userMenu/menu_controls.js';
import { LogBox } from './userMenu/menu_logbox.js';
import { initializeSettings } from './userMenu/menu_settings.js';

/**
 * Updates the visibility of header bar sections based on device type.
 */
export const updateHeaderBar = () => {
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

export const handleUserMenuRoute = (selectedLinkId) => {
	CTRL_STAT.mobileIsActive = false;
	updateModeUI(selectedLinkId);

	CTRL_STAT.currentPage = selectedLinkId;
	localStorage.setItem('user.menu.screen', selectedLinkId);

	const modeSwitchingPages = ['normal_ui_link', 'ai_training_link', 'autopilot_link', 'map_recognition_link', 'follow_link'];
	if (modeSwitchingPages.includes(selectedLinkId)) {
		const targetPage = isMobileDevice() ? '/mc' : '/normal_ui';
		const currentPage = $('main#application-content').data('current-page');

		if (currentPage === '/normal_ui' || currentPage === '/mc') {
			if (selectedLinkId === 'normal_ui_link') {
				loadContentBasedOnDevice();
			}
		} else {
			loadPage(targetPage, () => {
				if (selectedLinkId === 'normal_ui_link') {
					loadContentBasedOnDevice();
				} else {
					// Call the appropriate callback based on the device
					isMobileDevice() ? mcCallback() : normalUICallback();
				}
			});
		}
	} else {
		const pageMap = {
			settings_link: ['/menu_settings', initializeSettings],
			controls_link: ['/menu_controls', initDomElem],
			events_link: ['/menu_logbox', new LogBox()],
		};
		const [url, callback] = pageMap[selectedLinkId] || [];
		url && loadPage(url, callback);
	}
};

const loadContentBasedOnDevice = () => {
	const url = isMobileDevice() ? '/mc' : '/normal_ui';
	loadPage(url, () => {
		initComponents(); //as It is used between both UIs
		if (isMobileDevice()) {
			setupMobileController();
		} else {
			showHelp(); // Call the mobile callback
			// normalUICallback(); // Call the normal UI callback
		}
		CTRL_STAT.mobileIsActive = isMobileDevice();
	});
};
