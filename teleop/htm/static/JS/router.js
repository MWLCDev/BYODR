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
	constructor(helpMessageManager, messageContainerManager, advancedThemeManager, start_all_handlers) {
		this.helpMessageManager = helpMessageManager;
		this.messageContainerManager = messageContainerManager;
		this.advancedThemeManager = advancedThemeManager;
		this.start_all_handlers = start_all_handlers;
		this.bindDomActions();
		this.mode_to_nav_link = {
			normal_ui_link: 'manual drive',
			ai_training_link: 'ai training',
			autopilot_link: 'autopilot',
			map_recognition_link: 'map recognition',
			follow_link: 'follow',
		};
	}
	bindDomActions() {
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
		container
			.empty()
			.load(url, function (response, status, xhr) {
				if (status == 'success') {
					callback();
				} else {
					console.error('Failed to load the page:', xhr.status);
				}
			})
			.data('current-page', url);
	}

	updateModeUI(selectedLinkId) {
		if (!selectedLinkId) {
			console.error('Invalid ID provided for updateModeUI:', selectedLinkId);
			return;
		}
		if (isMobileDevice()) {
			$('#header_bar .left_section').show();
			$('#header_bar .right_section').show();
			if (['settings_link', 'controls_link', 'events_link'].includes(selectedLinkId)) {
				$('#header_bar .left_section').hide();
				$('#header_bar .right_section').hide();
			}
		} else {
			$('#header_bar .left_section').hide();
			$('#header_bar .right_section').hide();
		}

		$('.hamburger_menu_nav a').removeClass('active');
		$(`#${selectedLinkId}`).addClass('active');

		const activeNavLinkImageSrc = $(`#${selectedLinkId} img`).attr('src');
		if (activeNavLinkImageSrc) {
			$('.current_mode_img').attr('src', activeNavLinkImageSrc);
			$('.current_mode_text').text(this.mode_to_nav_link[selectedLinkId]);
		} else {
			console.error('No image found for ID:', selectedLinkId);
		}
	}

	handleUserMenuRoute(selectedLinkId) {
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
					// Run the callback after loading the content
					this.assignNavButtonActions(selectedLinkId);
				}
			} else {
				this.loadPage(targetPage, () => {
					if (selectedLinkId === 'normal_ui_link') {
						this.loadContentBasedOnDevice();
					} else {
						// Call the appropriate callback based on the device
						this.callbackBasedOnDevice();
					}
					// Run the callback after the page has been loaded
					this.assignNavButtonActions(selectedLinkId);
				});
			}
		} else {
			const pageMap = {
				settings_link: [
					'/menu_settings',
					() => {
						new UserSettingsManager();
						this.advancedThemeManager.bindActions();
					},
				],
				controls_link: ['/menu_controls', () => new ControlSettings()],
				events_link: ['/menu_logbox', () => new LogBox()],
			};
			const [url, callback] = pageMap[selectedLinkId] || [];
			if (url) {
				this.loadPage(url, () => {
					if (callback) callback();
					// Run the callback after the page has been loaded
					this.assignNavButtonActions(selectedLinkId);
				});
			}
		}
	}

	loadContentBasedOnDevice() {
		const url = isMobileDevice() ? '/mc' : '/normal_ui';
		this.loadPage(url, () => this.callbackBasedOnDevice());
	}

	callbackBasedOnDevice() {
		if (isMobileDevice()) {
			setupMobileController();
		} else {
			this.messageContainerManager.initEventHandlers();
			teleop_screen.set_normal_ui_elements();
			teleop_screen._init();
			this.start_all_handlers();
		}
	}

	/**
	 * Actions that are bonded to the navbar buttons only. They will control the switch for the features
	 */
	assignNavButtonActions(navLink) {
		//TODO: should add a filter here to remove all the styles related to the lat mode and reset them to the default values. So the new mode would only add its new styles on DOM.
		$('#mobile_controller_container #backward_square').removeClass('maneuver_square');
		$('#mobile_controller_container  .trail_canvas').show();
		$('#map_frame').hide();
		if (navLink == 'follow_link' && isMobileDevice()) followingNavButtonHandler.initializeDOM();
		else if (navLink == 'autopilot_link') autoNavigationNavButtonHandler.initializeDOM();
		else if (navLink == 'ai_training_link') maneuverTrainingNavButtonHandler.initializeDOM();
		else if (navLink == 'map_recognition_link') confidenceNavButtonHandler.initializeDOM();
		else if (navLink == 'phone_controller_link') {
			this.helpMessageManager.connectPhoneMessage();
			this.updateModeUI('normal_ui_link');
		}
	}
}
