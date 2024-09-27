import { isMobileDevice } from './Index/index_a_utils.js';
import { roverUI } from './Index/index_c_screen.js';
import { setupMobileController } from './mobileController/mobileController_a_app.js';
import { autoNavigationNavButtonHandler } from './mobileController/feature/mobileController_f_auto_navigation.js';
import { confidenceNavButtonHandler } from './mobileController/feature/mobileController_f_confidence.js';
import { followingNavButtonHandler } from './mobileController/feature/mobileController_f_following.js';
import { maneuverTrainingNavButtonHandler } from './mobileController/feature/mobileController_f_maneuver_training.js';
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
		this.previousPage = null;
		this.bindDomActions();
		this.mode_to_nav_link = {
			normal_ui_link: 'manual drive',
			ai_training_link: 'ai training',
			auto_navigation_link: 'autopilot',
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
			$('.rover_speed_label').css('font-size', '5px');
			$('.inf_speed_label').css('font-size', '5px');
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

		// Find the SVG inside the selected link
		const $selectedNavLink = $(`#${selectedLinkId}`);
		const $svg = $selectedNavLink.find('svg.nav_icon');

		if ($svg.length > 0) {
			// Clone the SVG and insert it into the current_mode_img element
			const $clonedSvg = $svg.clone();
			$('.current_mode_img').empty().append($clonedSvg);
		} else {
			console.error('No SVG icon found for ID:', selectedLinkId);
		}
	}

	switchFolState(selectedLinkId) {
		try {
			if (this.previousPage === 'follow_link' && selectedLinkId !== 'follow_link') {
				followingNavButtonHandler.sendSwitchFollowingRequest('inactive');
			}
		} catch (error) {
			console.error('problem while sending fol stopping signal:', error);
		}
	}

	handleUserMenuRoute(selectedLinkId) {
		this.switchFolState(selectedLinkId);
		this.updateModeUI(selectedLinkId);

		CTRL_STAT.currentPage = selectedLinkId;
		localStorage.setItem('user.menu.screen', selectedLinkId);

		const modeSwitchingPages = ['normal_ui_link', 'ai_training_link', 'auto_navigation_link', 'map_recognition_link', 'follow_link'];
		if (modeSwitchingPages.includes(selectedLinkId)) {
			const targetPage = isMobileDevice() ? '/mc' : '/normal_ui';
			const currentPage = $('main#application_content').data('current-page');

			if (currentPage === '/normal_ui' || currentPage === '/mc') {
				if (selectedLinkId === 'normal_ui_link') {
					this.loadContentBasedOnDevice();
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
					this.assignNavButtonActions(selectedLinkId);
				});
			}
		}
		this.previousPage = selectedLinkId;
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
			roverUI.init();
			roverUI.setNormalUIElements();
			this.start_all_handlers();
		}
	}

	/**
	 * Removes all mode-related classes from the body element dynamically.
	 */
	resetStyles() {
		// Define the pattern for mode-related classes
		const modeClassPattern = /-\b(feature|mode)\b/;

		// Get the current list of classes on the body element
		const bodyClasses = $('body').attr('class') ? $('body').attr('class').split(/\s+/) : [];

		// Filter and remove all classes that match the pattern
		bodyClasses.forEach((className) => {
			if (modeClassPattern.test(className)) {
				$('body').removeClass(className);
			}
		});
	}

	/**
	 * Actions that are bonded to the navbar buttons only.
	 */
	assignNavButtonActions(navLink) {
		this.resetStyles();
		if (navLink == 'follow_link' && isMobileDevice()) followingNavButtonHandler.initializeDOM();
		else if (navLink == 'auto_navigation_link') autoNavigationNavButtonHandler.initializeDOM();
		else if (navLink == 'ai_training_link') maneuverTrainingNavButtonHandler.initializeDOM();
		else if (navLink == 'map_recognition_link') confidenceNavButtonHandler.initializeDOM();
		else if (navLink == 'phone_controller_link') {
			this.helpMessageManager.connectPhoneMessage();
			this.updateModeUI('normal_ui_link');
		}
	}
}
