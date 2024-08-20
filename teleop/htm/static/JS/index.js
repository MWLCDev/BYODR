import { dev_tools, isMobileDevice, network_utils, page_utils, socket_utils } from './Index/index_a_utils.js';
import { setupThemeManagers } from './Index/index_c_screen.js';
import { navigator_start_all } from './Index/index_d_navigator.js';
import { teleop_start_all } from './Index/index_e_teleop.js';
import { init_mjpeg } from './Index/index_video_mjpeg.js';
import { h264_start_all, h264_stop_all } from './Index/index_video_hlp.js';
import { mjpeg_start_all, mjpeg_stop_all } from './Index/index_video_mjpeg.js';
import CTRL_STAT from './mobileController/mobileController_z_state.js'; // Stands for control state
import { Router } from './router.js';

function initComponents() {
	try {
		[socket_utils, dev_tools, page_utils].forEach((component) => component._init());
		init_mjpeg();
	} catch (error) {
		console.error('Error while initializing components:', error);
	}
}
let handlersRunning = false;
function start_all_handlers() {
	console.log('Attempting to start all handlers');
	if (!handlersRunning) {
		console.log('Handlers not running, starting now');
		try {
			mjpeg_start_all();
			h264_start_all();
			handlersRunning = true;
			console.log('All handlers started successfully');
		} catch (error) {
			console.error('Error starting handlers:', error);
		}
	} else {
		handlersRunning = false;
		start_all_handlers();
		console.log('Handlers already running. Will force restart');
	}
}

function stop_all_handlers() {
	console.log('Attempting to stop all handlers');
	if (handlersRunning) {
		console.log('Handlers running, stopping now');
		try {
			mjpeg_stop_all();
			h264_stop_all();
			handlersRunning = false;
			console.log('All handlers stopped successfully');
		} catch (error) {
			console.error('Error stopping handlers:', error);
		}
	} else {
		console.log('Handlers not running, skipping stop');
	}
}
function handleVisibilityChange() {
	if (CTRL_STAT.currentPage == 'normal_ui_link') {
		if (document.hidden) {
			stop_all_handlers();
		} else {
			start_all_handlers();
		}
	}
}

function showSSID() {
	network_utils
		.getSSID()
		.then((ssid) => $('#header_bar #current_seg_name').text(ssid))
		.catch((error) => console.error('Failed to fetch SSID:', error));
}

$(window).on('load', () => {
	['phone_controller_link'].forEach((id) => $(`#${id}`)[isMobileDevice() ? 'hide' : 'show']());
	let { helpMessageManager, messageContainerManager, advancedThemeManager } = setupThemeManagers();
	const router = new Router(helpMessageManager, messageContainerManager, advancedThemeManager, start_all_handlers, stop_all_handlers);

	router.handleUserMenuRoute(localStorage.getItem('user.menu.screen') || 'normal_ui_link'); // Need to have a default value for the homepage

	document.addEventListener('visibilitychange', handleVisibilityChange, false);
	$(window).on('focus', start_all_handlers);
	$(window).on('blur', stop_all_handlers);

	showSSID();
	initComponents();
	navigator_start_all();
	teleop_start_all();
});
