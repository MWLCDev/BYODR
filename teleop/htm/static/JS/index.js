import { dev_tools, isMobileDevice, network_utils, page_utils, socket_utils } from './Index/index_a_utils.js';
import { helpMessageManager, messageContainerManager, advancedThemeManager } from './Index/index_c_screen.js';
import { navigator_start_all } from './Index/index_d_navigator.js';
import { teleop_start_all } from './Index/index_e_teleop.js';
import { h264_start_all, h264_stop_all } from './Index/index_video_hlp.js';
import { init_mjpeg, mjpeg_start_all, mjpeg_stop_all } from './Index/index_video_mjpeg.js';
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

function start_all_handlers() {
	try {
		if (CTRL_STAT.currentPage == 'normal_ui_link') {
			mjpeg_start_all();
			h264_start_all();
		}
	} catch (error) {
		console.error('Error starting handlers:', error);
	}
}

function stop_all_handlers() {
	try {
		if (CTRL_STAT.currentPage == 'normal_ui_link') {
			mjpeg_stop_all();
			h264_stop_all();
		}
	} catch (error) {
		console.error('Error stopping handlers:', error);
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
	const router = new Router(helpMessageManager, messageContainerManager, advancedThemeManager, start_all_handlers);

	router.handleUserMenuRoute(localStorage.getItem('user.menu.screen') || 'normal_ui_link'); // Need to have a default value for the homepage

	document.addEventListener('visibilitychange', handleVisibilityChange, false);
	$(window).on('focus', start_all_handlers);
	$(window).on('blur', stop_all_handlers);

	showSSID();
	initComponents();
	navigator_start_all();
	teleop_start_all();
});
