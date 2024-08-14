import { isMobileDevice } from './Index/index_a_utils.js';
import { teleop_screen } from './Index/index_c_screen.js';
import { setupMobileController } from './mobileController/mobileController_a_app.js';
import { autoNavigationNavButtonHandler } from './mobileController/mobileController_f_auto_navigation.js';
import { confidenceNavButtonHandler } from './mobileController/mobileController_f_confidence.js';
import { followingNavButtonHandler } from './mobileController/mobileController_f_following.js';
import { maneuverTrainingNavButtonHandler } from './mobileController/mobileController_f_maneuver_training.js';
import CTRL_STAT from './mobileController/mobileController_z_state.js';
import { ControlSettings } from './userMenu/menu_controls.js';
import { LogBox } from './userMenu/menu_logbox.js';
import { UserSettingsManager } from './userMenu/menu_settings.js';

export class Router {
	constructor(helpMessageManager, messageContainerManager) {
		this.helpMessageManager = helpMessageManager;
		this.messageContainerManager = messageContainerManager;
		$('.hamburger_menu_nav a').click((event) => {
			this.handleUserMenuRoute(event.target.id);
			this.assignNavButtonActions(event.target.id);
		});
	}

	updateHeaderBar() {
		const sections = ['left_section', 'right_section'];
		sections.forEach((section) => $(`#header_bar .${section}`)[isMobileDevice() ? 'show' : 'hide']());
	}

	/**
	 * Loads a page into the main content area and executes a callback if provided.
	 * @param {string} url - The URL of the page to load.
	 * @param {Function} [callback] - Optional callback to execute after loading the page.
	 */
	loadPage(url, callback) {
		const container = $('main#application_content');
		container.empty().load(url, callback).data('current-page', url);
	}

	updateModeUI(selectedLinkId) {
		if (!selectedLinkId) {
			console.error('Invalid ID provided for updateModeUI:', selectedLinkId);
			return;
		}

		$('.hamburger_menu_nav a').removeClass('active');
		$(`#${selectedLinkId}`).addClass('active');

		const activeImageSrc = $(`#${selectedLinkId} img`).attr('src');
		if (activeImageSrc) {
			$('.current_mode_img').attr('src', activeImageSrc);
		} else {
			console.error('No image found for ID:', selectedLinkId);
		}
	}

	handleUserMenuRoute(selectedLinkId) {
		CTRL_STAT.mobileIsActive = false;
		this.updateModeUI(selectedLinkId);

		CTRL_STAT.currentPage = selectedLinkId;
		localStorage.setItem('user.menu.screen', selectedLinkId);

		const modeSwitchingPages = ['normal_ui_link', 'ai_training_link', 'autopilot_link', 'map_recognition_link', 'follow_link'];
		if (modeSwitchingPages.includes(selectedLinkId)) {
			const targetPage = isMobileDevice() ? '/mc' : '/normal_ui';
			const currentPage = $('main#application_content').data('current-page');

			if (currentPage === '/normal_ui' || currentPage === '/mc') {
				if (selectedLinkId === 'normal_ui_link') {
					this.loadContentBasedOnDevice();
				}
			} else {
				this.loadPage(targetPage, () => {
					if (selectedLinkId === 'normal_ui_link') {
						this.loadContentBasedOnDevice();
					} else {
						// Call the appropriate callback based on the device

						isMobileDevice() ? setupMobileController() : showHelp();
					}
				});
			}
		} else {
			const pageMap = {
				settings_link: ['/menu_settings', () => new UserSettingsManager()],
				controls_link: ['/menu_controls', () => new ControlSettings()],
				events_link: ['/menu_logbox', () => new LogBox()],
			};
			const [url, callback] = pageMap[selectedLinkId] || [];
			url && this.loadPage(url, callback);
		}
	}

	loadContentBasedOnDevice() {
		const url = isMobileDevice() ? '/mc' : '/normal_ui';
		this.loadPage(url, () => {
			if (isMobileDevice()) {
				setupMobileController();
			} else {
				this.messageContainerManager.initEventHandlers();
				teleop_screen.set_normal_ui_elements();
				teleop_screen._init();
			}
			CTRL_STAT.mobileIsActive = isMobileDevice();
		});
	}
	/**
	 * Actions that are bonded to the navbar buttons only. They will control the switch for the features
	 */
	assignNavButtonActions(navLink) {
		if (navLink == 'follow_link') followingNavButtonHandler.initializeDOM();
		else if (navLink == 'autopilot_link') autoNavigationNavButtonHandler.initializeDOM();
		else if (navLink == 'ai_training_link') maneuverTrainingNavButtonHandler.initializeDOM();
		else if (navLink == 'map_recognition_link') confidenceNavButtonHandler.initializeDOM();
		else if (navLink == 'phone_controller_link') {
			this.helpMessageManager.connectPhoneMessage();
			$('.message_container').removeClass('hidden').hide().fadeIn(500);
			closeMessageContainer();
			console.log('clicked');
		}
	}
}
