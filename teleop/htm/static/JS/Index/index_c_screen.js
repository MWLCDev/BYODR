import CTRL_STAT from '../mobileController/mobileController_z_state.js'; // Stands for control state

import { isMobileDevice, page_utils } from './index_a_utils.js';
import { gamepad_controller } from './index_b_gamepad.js';
import { gamepad_socket } from './index_e_teleop.js';

class DarkThemeManager {
	constructor() {
		this.darkModeCheckbox = document.querySelector('#nav_dark_mode_toggle_container input[type="checkbox"]');
		this.body = document.body;
		this.init();
	}

	init() {
		this.loadSavedState();
		this.addEventListeners();
	}

	loadSavedState() {
		const isDarkMode = localStorage.getItem('darkMode') === 'enabled';
		this.darkModeCheckbox.checked = isDarkMode;
		this.setTheme(isDarkMode);
	}

	addEventListeners() {
		this.darkModeCheckbox.addEventListener('change', () => this.toggleTheme());
	}

	toggleTheme() {
		const isDarkMode = this.darkModeCheckbox.checked;
		this.setTheme(isDarkMode);
		localStorage.setItem('darkMode', isDarkMode ? 'enabled' : 'disabled');
	}

	setTheme(isDarkMode) {
		this.body.classList.toggle('dark-theme', isDarkMode); //Add dark mode to body only
	}
}

class AdvancedThemeManager {
	constructor() {
		this.body = document.body;
		this.isAdvancedMode = true;
		this.loadAdvancedThemeSavedState();
		this.setAdvancedTheme();
	}

	bindActions() {
		this.advancedModeCheckBox = document.getElementById('pro-view-toggle-button');
		this.toggleStatus = $('#pro-view-toggle-status');
		this.addEventListeners();
		this.toggleAdvancedTheme();
	}

	loadAdvancedThemeSavedState() {
		const savedState = localStorage.getItem('advancedMode');
		this.isAdvancedMode = savedState === 'true';
	}

	addEventListeners() {
		this.advancedModeCheckBox.addEventListener('change', () => {
			this.isAdvancedMode = this.advancedModeCheckBox.checked;
			this.toggleAdvancedTheme();
		});
	}

	toggleAdvancedTheme() {
		this.changeToggleUI();
		this.setAdvancedTheme();
		localStorage.setItem('advancedMode', this.isAdvancedMode.toString());
	}

	changeToggleUI() {
		if (this.isAdvancedMode) {
			this.toggleStatus.text('on');
			this.advancedModeCheckBox.checked = true;
		} else {
			this.toggleStatus.text('off');
			this.advancedModeCheckBox.checked = false;
		}
		this.setAdvancedTheme();
	}

	setAdvancedTheme() {
		if (this.isAdvancedMode) {
			$('body').removeClass('advanced-theme');
		} else {
			$('body').addClass('advanced-theme');
		}
	}
}

class NavigationManager {
	//Deal with the navigation bar and toggle the blur motion when the navigation bar is active
	constructor() {
		this.toggleBtn = document.getElementById('hamburger_menu_toggle');
		this.nav = document.querySelector('.hamburger_menu_nav');
		this.userMenu = document.getElementById('application_content');
		this.headerBar = document.getElementById('header_bar');
		this.navLinks = document.querySelectorAll('.hamburger_menu_nav a');

		this.setNavHeight(); // Set initial height
		this.addEventListeners();
	}

	addEventListeners() {
		this.toggleBtn.addEventListener('click', () => this.toggleSidebar());
		this.navLinks.forEach((link) => {
			link.addEventListener('click', () => this.toggleSidebar());
		});
		document.addEventListener('click', (event) => this.handleOutsideClick(event));
		window.addEventListener('resize', () => this.setNavHeight()); // Resize listener
	}

	setNavHeight() {
		this.nav.style.height = `${window.innerHeight}px`;
	}

	toggleSidebar() {
		this.nav.classList.toggle('active');
		this.toggleBtn.classList.toggle('active');
		this.userMenu.classList.toggle('expanded');
		this.headerBar.classList.toggle('expanded');
	}

	handleOutsideClick(event) {
		const isClickInsideNav = this.nav.contains(event.target);
		const isClickToggleBtn = this.toggleBtn.contains(event.target);
		if (!isClickInsideNav && !isClickToggleBtn && this.nav.classList.contains('active')) {
			this.toggleSidebar();
		}
	}
}

class HelpMessageManager {
	//Define the types of message that will show in the help menu
	constructor() {
		this.help_message_img = $('.message_container img');
		this.help_message_grid = document.querySelector('.help_message_grid');
		this.manualModeMessages();
		$(document).mouseup((e) => {
			this.onClickOutside(e);
		});
	}

	manualModeMessages() {
		const messages = [
			'Drive forward: Press 14 slowly down',
			'Drive backwards: Press 1 slowly down',
			'Steering: Move 7 around',
			'Camera to drive position: Press 6',
			'Switch between cameras: Press 10 or 11',
			'Move selected camera around: Move 8 around',
			'Switch to autopilot mode: Press 3',
			'Capture the current frame with the front camera: Press 13',
			//TODO: see if more styles will be added
		];
		this.updateMessages(messages, true);
	}

	connectPhoneMessage() {
		const messages = ['1-open setting menu', '2- Add new wifi network', '3-Add username of the segment you see on the top', '4-In the password field, write the password that was sent in your email'];

		// First update the messages and then show the message container
		this.updateMessages(messages, false);
		this.showMessageContainer();
	}

	// Explicitly set application content state instead of toggling
	expandApplicationContent() {
		$('#application_content').addClass('expanded');
		$('#hamburger_menu_toggle').addClass('expanded');
		$('#header_bar').addClass('expanded');
	}

	collapseApplicationContent() {
		$('#application_content').removeClass('expanded');
		$('#hamburger_menu_toggle').removeClass('expanded');
		$('#header_bar').removeClass('expanded');
	}
	// Add a new method to ensure consistent handling of showing the container
	showMessageContainer() {
		const container = $('.message_container');
		container.removeClass('hidden').fadeIn(500);
		this.expandApplicationContent(); // Ensure the application content is expanded when showing
	}

	hideMessageContainer() {
		const container = $('.message_container');
		container.fadeOut(500, () => {
			container.addClass('hidden');
			this.collapseApplicationContent(); // Collapse content when the container is hidden
		});
	}

	// Private method to update the message grid
	updateMessages(messages, show_help_img) {
		if (show_help_img) {
			this.help_message_img.show();
		} else {
			this.help_message_img.hide();
		}
		this.help_message_grid.innerHTML = '';
		messages.forEach((msg) => {
			const p = document.createElement('p');
			p.className = 'message';
			p.textContent = msg;
			this.help_message_grid.appendChild(p);
		});
	}

	// Handle click outside the message container to close it
	onClickOutside(e) {
		var container = $('.message_container');
		if (container.is(':visible') && !container.is(e.target) && container.has(e.target).length === 0) {
			this.hideMessageContainer();
		}
	}
}

class MessageContainerManager {
	constructor(helpMessageManager) {
		this.helpMessageManager = helpMessageManager;
	}

	initEventHandlers() {
		try {
			$('.toggle_help_message').click(() => {
				this.helpMessageManager.manualModeMessages();
				this.toggleMessageContainer();
			});

			document.querySelector('.close_btn').addEventListener('click', () => {
				this.hideMessageContainer();
			});

			$(document).mouseup((e) => {
				this.onClickOutside(e);
			});
		} catch (error) {
			console.error('Error while init: ', error);
		}
	}

	// Toggle the visibility of the message container
	toggleMessageContainer() {
		$('.message_container').removeClass('hidden').hide().fadeIn(500);
		this.toggleApplicationContent();
	}

	// Hide the message container with a fade-out effect
	hideMessageContainer() {
		$('.message_container').fadeOut(500, () => {
			$('.message_container').addClass('hidden');
		});
		this.toggleApplicationContent();
	}

	// Toggle the application content and header bar expansion
	toggleApplicationContent() {
		$('#application_content').toggleClass('expanded');
		$('#hamburger_menu_toggle').toggleClass('expanded');
		$('#header_bar').toggleClass('expanded');
	}

	// Handle click outside the message container to close it
	onClickOutside(e) {
		var container = $('.message_container');
		if (container.is(':visible') && !container.is(e.target) && container.has(e.target).length === 0) {
			this.hideMessageContainer();
		}
	}
}

class PathRenderer {
	// Method to render a trapezoid shape
	_renderTrapezoid(ctx, positions, fill = 'rgba(100, 217, 255, 0.3)') {
		if (!ctx || !positions || positions.length !== 4) {
			console.error('Invalid parameters passed to _renderTrapezoid');
			return;
		}

		ctx.lineWidth = 0.5;
		ctx.strokeStyle = 'rgb(255, 255, 255)';
		ctx.fillStyle = fill;
		ctx.beginPath();
		ctx.moveTo(positions[0][0], positions[0][1]);
		ctx.lineTo(positions[1][0], positions[1][1]);
		ctx.lineTo(positions[2][0], positions[2][1]);
		ctx.lineTo(positions[3][0], positions[3][1]);
		ctx.closePath();
		ctx.stroke();
		ctx.fill();
	}

	// Method to get constants based on the vehicle type
	_getConstants() {
		const constants = {
			rover1: [400 / 640, 120 / 480, 6 / 640, 8 / 480, 0.65, 0.65, 0.8, 0.7, 65 / 640, 2 / 480],
		};

		return constants.rover1;
	}

	// Method to render the path
	renderPath(ctx, path) {
		if (!ctx || !path || !Array.isArray(path)) {
			console.error('Invalid parameters passed to renderPath');
			return;
		}

		const canvas = ctx.canvas;
		const [tzWidthFactor, tzHeightFactor, gapFactor, cutFactor, taper, heightShrink, gapShrink, cutShrink, wSteeringFactor, hSteeringFactor] = this._getConstants();

		// Calculating dimensions based on canvas size
		const tzWidth = tzWidthFactor * canvas.width;
		const tzHeight = tzHeightFactor * canvas.height;
		const gap = gapFactor * canvas.width;
		const cut = cutFactor * canvas.height;
		const wSteering = wSteeringFactor * canvas.width;
		const hSteering = hSteeringFactor * canvas.height;

		// Start from the middle of the base of the trapezoid.
		let baseAx = canvas.width / 2 - tzWidth / 2;
		let baseAy = canvas.height - gap;
		let baseBx = baseAx + tzWidth;
		let baseBy = baseAy;
		let idx = 0;

		path.forEach((steeringValue) => {
			// Calculate width of the base and offsets for the next step
			// Start in the lower left corner and draw counter clockwise.

			const baseWidth = baseBx - baseAx;
			const offsetWidth = (baseWidth - baseWidth * taper) / 2;
			const height = tzHeight * Math.pow(heightShrink, idx);
			const steerDx = wSteering * steeringValue;
			const steerDy = hSteering * steeringValue;

			// Calculate the coordinates for the trapezoid
			const cx = baseBx - offsetWidth + steerDx;
			const cy = baseBy - height + (steeringValue > 0 ? steerDy : 0);
			const dx = baseAx + offsetWidth + steerDx;
			const dy = baseAy - height - (steeringValue < 0 ? steerDy : 0);

			// Render the trapezoid
			this._renderTrapezoid(ctx, [
				[baseAx, baseAy],
				[baseBx, baseBy],
				[cx, cy],
				[dx, dy],
			]);

			// Update the base coordinates for the next step
			// The next step starts from the top of the previous with gap.
			const cutShrinked = 0.5 * cut * Math.pow(cutShrink, idx);
			const gapShrinked = gap * Math.pow(gapShrink, idx);

			baseAx = dx + cutShrinked;
			baseAy = dy - gapShrinked;
			baseBx = cx - cutShrinked;
			baseBy = cy - gapShrinked;

			idx++;
		});
	}
}

class RoverUI {
	//Changes the UI elements based on the backend
	constructor() {
		this.commandTurn = null;
		this.serverMessageListeners = [];
		this.isConnectionOk = 0;
		this.controllerStatus = 0;
		this.cMsgConnectionLost = 'Connection lost - please wait or refresh the page.';
		this.cMsgControllerErr = 'Controller not detected - please press a button on the device.';
		this.cMsgTeleopViewOnly = 'Another user is in control - you can remain as viewer or take over.';
		this.infLastServerMessage = null;
		this.activeCamera = null;
	}

	init() {
		try {
			this.pathRenderer = new PathRenderer();
			this.controllerStatus = gamepad_controller.is_active();
			$('#video_stream_type').val(page_utils.get_stream_type() === 'mjpeg' ? 'mjpeg' : 'h264');
			$('#message_box_button_take_control').click(() => gamepad_socket._request_take_over_control());
		} catch (error) {
			console.error('Error in RoverUI.init():', error);
		}
	}

	getElement(selector, retries = 99) {
		// Helper function to safely select an element
		let element = null;
		for (let i = 0; i < retries; i++) {
			element = $(selector);
			if (element.length > 0) {
				break;
			}
		}
		if (element.length === 0) {
			console.error(`Element not found: ${selector}`);
		}
		return element;
	}

	setNormalUIElements() {
		try {
			const elements = {
				viewportContainer: this.getElement('div#viewport_container'),
				debugDriveBar: this.getElement('div#debug_drive_bar'),
				debugDriveValues: this.getElement('div#debug_drive_values'),
				messageBoxContainer: this.getElement('div#message_box_container'),
				overlayImage: this.getElement('img#mjpeg_camera_preview_image'),
				overlayCenterDistance0: this.getElement('div#overlay_center_distance0'),
				overlayCenterDistance1: this.getElement('div#overlay_center_distance1'),
				overlayLeftMarker0: this.getElement('div#overlay_left_marker0'),
				overlayLeftMarker1: this.getElement('div#overlay_left_marker1'),
				overlayRightMarker0: this.getElement('div#overlay_right_marker0'),
				overlayRightMarker1: this.getElement('div#overlay_right_marker1'),
				messageBoxMessage: this.getElement('div#message_box_message'),
				buttonTakeControl: this.getElement('input#message_box_button_take_control'),
			};

			// Assign the elements to the corresponding class properties
			this.elViewportContainer = elements.viewportContainer;
			this.elDriveBar = elements.debugDriveBar;
			this.elDriveValues = elements.debugDriveValues;
			this.elMessageBoxContainer = elements.messageBoxContainer;
			this.overlayImage = elements.overlayImage;
			this.elMessageBoxMessage = elements.messageBoxMessage;
			this.elButtonTakeControl = elements.buttonTakeControl;
			this.overlayCenterMarkers = [elements.overlayCenterDistance0, elements.overlayCenterDistance1];
			this.overlayLeftMarkers = [elements.overlayLeftMarker0, elements.overlayLeftMarker1];
			this.overlayRightMarkers = [elements.overlayRightMarker0, elements.overlayRightMarker1];
		} catch (error) {
			console.error('Error in RoverUI.setNormalUIElements():', error);
		}
	}

	renderDistanceIndicators(activeCamera) {
		const show = activeCamera == 'front';
		if (!isMobileDevice()) {
			[this.overlayCenterMarkers, this.overlayLeftMarkers, this.overlayRightMarkers].flat().forEach(function (marker) {
				if (show) {
					marker.show();
				} else {
					marker.hide();
				}
			});
		}
	}

	controllerUpdate() {
		try {
			let showMessage = false;
			let showButton = false;
			if (this.elMessageBoxMessage !== undefined && this.elMessageBoxMessage.length > 0) {
				if (!this.isConnectionOk) {
					this.elMessageBoxMessage.text(this.cMsgConnectionLost);
					this.elMessageBoxMessage.removeClass();
					this.elMessageBoxMessage.addClass('error_message');
					showMessage = true;
				} else if (this.controllerStatus === 0) {
					this.elMessageBoxMessage.text(this.cMsgControllerErr);
					this.elMessageBoxMessage.removeClass();
					this.elMessageBoxMessage.addClass('warning_message');
					showMessage = true;
				} else if (this.controllerStatus === 2) {
					this.elMessageBoxMessage.text(this.cMsgTeleopViewOnly);
					this.elMessageBoxMessage.removeClass();
					this.elMessageBoxMessage.addClass('warning_message');
					showMessage = true;
					showButton = true;
				}
				if (showMessage) {
					if (showButton) {
						this.elButtonTakeControl.show();
					} else {
						this.elButtonTakeControl.hide();
					}
					this.elMessageBoxContainer.show();
				} else {
					this.elMessageBoxContainer.hide();
				}
			}
		} catch (error) {
			console.error('Error in RoverUI.controllerUpdate():', error);
		}
	}

	onCanvasInit(width, height) {
		$('span#debug_screen_dimension').text(width + 'x' + height);
	}

	canvasUpdate(ctx) {
		try {
			const serverMessage = this.infLastServerMessage;
			const autopilotActive = serverMessage !== undefined && serverMessage._is_on_autopilot;
			if (autopilotActive && this.activeCamera === 'front') {
				this.pathRenderer.renderPath(ctx, serverMessage.nav_path);
			}
		} catch (error) {
			console.error('Error in RoverUI.canvasUpdate():', error);
		}
	}
}

class InferenceHandling {
	constructor(roverUI) {
		this.roverUI = roverUI; // Dependency injection for shared UI elements and functionality
	}

	handleServerMessage(infMessage) {
		try {
			this.roverUI.infLastServerMessage = infMessage;
			if (infMessage.inf_surprise !== undefined) {
				this.updateInferenceAdvancedViewUI(infMessage);
			}
			$('p.rover_speed_value').text(infMessage.vel_y.toFixed(1));

			// Handle autopilot-related UI changes
			if (infMessage._is_on_autopilot) {
				this.updateAutopilotUI(infMessage);
				this.toggleMobileUI(true);
			} else {
				this.toggleMobileUI(false);
			}
			this.updateSteeringWheelRotation(infMessage.vel_y, infMessage.ste);
		} catch (error) {
			console.error('Error in InferenceHandling.handleServerMessage():', error);
		}
	}

	updateInferenceAdvancedViewUI(infMessage) {
		$('span#inference_brake_critic').text(infMessage.inf_brake_critic.toFixed(2));
		$('span#inference_obstacle').text(infMessage.inf_brake.toFixed(2));
		$('span#inference_surprise').text(infMessage.inf_surprise.toFixed(2));
		$('span#inference_critic').text(infMessage.inf_critic.toFixed(2));
		$('span#inference_fps').text(infMessage.inf_hz.toFixed(0));
		$('span#inference_desired_speed').text(infMessage.des_speed.toFixed(1));

		this.applyInferenceColorScheme(infMessage.inf_brake_penalty, infMessage.inf_steer_penalty);
	}

	applyInferenceColorScheme(brakePenalty, steerPenalty) {
		const brakeColors = this.calculateColorScheme(brakePenalty);
		const steerColors = this.calculateColorScheme(steerPenalty);

		$('span#inference_brake_critic').css('color', brakeColors);
		$('span#inference_obstacle').css('color', brakeColors);
		$('span#inference_surprise').css('color', steerColors);
		$('span#inference_critic').css('color', steerColors);
	}

	calculateColorScheme(penalty) {
		const red = Math.min(255, penalty * 2 * 255);
		const green = (1 - 2 * Math.max(0, penalty - 0.5)) * 255;
		return `rgb(${red}, ${green}, 0)`;
	}

	updateAutopilotUI(infMessage) {
		$('p.inf_speed_value').text(`${infMessage.max_speed.toFixed(1)} KM`);
		this.roverUI.renderDistanceIndicators('front');
	}

	formatTime(totalSeconds) {
		const hours = Math.floor(totalSeconds / 3600);
		const mins = Math.floor((totalSeconds % 3600) / 60);
		const secs = Math.floor(totalSeconds % 60);
		const zfH = ('00' + hours).slice(-2);
		const zfM = ('00' + mins).slice(-2);
		const zfS = ('00' + secs).slice(-2);

		return `${zfH}:${zfM}:${zfS}`;
	}

	updateSteeringWheelRotation(speed, steeringAngle) {
		try {
			const elSteeringWheel = $('img.steeringWheel');
			let displayRotation;

			if (speed >= 0) {
				displayRotation = Math.floor(steeringAngle * 90.0);
			} else {
				displayRotation = Math.floor(steeringAngle * -90.0 - 180);
			}

			elSteeringWheel.css('transform', `rotate(${displayRotation}deg)`);
		} catch (error) {
			console.error('Error in InferenceHandling.updateSteeringWheelRotation():', error);
		}
	}

	toggleMobileUI(active) {
		if (CTRL_STAT.currentPage == 'ai_training_link') {
			if (active) {
				$('body').addClass('training-started');
			} else if (!active) {
				$('body').removeClass('training-started');
			}
		}
		if (CTRL_STAT.currentPage == 'auto_navigation_link') {
			if (active) {
				$('body').addClass('navigation-started');
			} else if (!active) {
				$('body').removeClass('navigation-started');
			}
		}
	}
}

class CameraControls {
	constructor(roverUI) {
		this.roverUI = roverUI; // Dependency injection for shared UI elements and functionality
		this.activeCamera = 'front'; // The one in main view
		this.selectedCamera = null; //The one being controlled
		this.cameraSelectionListeners = [];
		this.cameraActivationListeners = [];
		this._cameraCycleTimer = null;
		this._photoSnapshotTimer = null;

		// Set the default active camera in RoverUI during initialization
		this.roverUI.activeCamera = this.activeCamera;

		// Add listeners to update RoverUI whenever the camera changes
		this.addCameraActivationListener((name) => {
			this.roverUI.activeCamera = name;
			this.roverUI.renderDistanceIndicators(name);
		});
	}
	selectNextCamera() {
		const nextCamera = this.selectedCamera == null ? this.activeCamera : this.selectedCamera === 'front' ? 'rear' : 'front';
		this.selectCamera(nextCamera);
	}

	selectCamera(name) {
		this.selectedCamera = name;
		this.cameraSelectionListeners.forEach((cb) => cb());
		this.onCameraSelection();
	}

	cycleCameraSelection() {
		this.selectNextCamera();
		if (this.selectedCamera != null) {
			console.log(`Camera ${this.selectedCamera} is selected for PTZ control.`);
		}
		this._cameraCycleTimer = null;
	}

	scheduleCameraCycle() {
		if (this._cameraCycleTimer == null) {
			this._cameraCycleTimer = setTimeout(() => this.cycleCameraSelection(), 150);
		}
	}

	schedulePhotoSnapshotEffect() {
		if (this._photoSnapshotTimer != null) {
			clearTimeout(this._photoSnapshotTimer);
		}
		this._photoSnapshotTimer = setTimeout(() => {
			this.roverUI.elViewportContainer.fadeOut(50).fadeIn(50);
		}, 130);
	}

	handleCameraCommand(joystickCommand) {
		if (joystickCommand != null && joystickCommand.arrow_left) {
			this.scheduleCameraCycle();
		} else if (joystickCommand != null && joystickCommand.arrow_right) {
			this.scheduleCameraCycle();
		}
		if (joystickCommand != null && joystickCommand.button_right) {
			this.schedulePhotoSnapshotEffect();
		}
	}

	onCameraSelection() {
		const active = this.activeCamera;
		const selected = this.selectedCamera;
		this.roverUI.elViewportContainer.removeClass('selected');
		this.roverUI.overlayImage.removeClass('selected');
		if (selected === active) {
			this.roverUI.elViewportContainer.addClass('selected');
		} else if (selected != null) {
			this.roverUI.overlayImage.addClass('selected');
		}
	}

	addCameraActivationListener(cb) {
		this.cameraActivationListeners.push(cb);
	}

	addCameraSelectionListener(cb) {
		this.cameraSelectionListeners.push(cb);
	}

	toggleCamera() {
		const name = this.activeCamera === 'front' ? 'rear' : 'front';
		this.activeCamera = name;
		this.selectedCamera = null;
		this.roverUI.renderDistanceIndicators(name);
		this.cameraActivationListeners.forEach((cb) => cb(name));
		this.cameraSelectionListeners.forEach((cb) => cb());
	}
}

new NavigationManager();
new DarkThemeManager();
const advancedThemeManager = new AdvancedThemeManager();
const helpMessageManager = new HelpMessageManager();
const messageContainerManager = new MessageContainerManager(helpMessageManager);
const roverUI = new RoverUI();
const inferenceHandling = new InferenceHandling(roverUI);
const cameraControls = new CameraControls(roverUI);

export { advancedThemeManager, cameraControls, helpMessageManager, inferenceHandling, messageContainerManager, roverUI };
