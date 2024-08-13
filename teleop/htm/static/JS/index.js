import { dev_tools, page_utils, socket_utils, network_utils, isMobileDevice } from './Index/index_a_utils.js';
import { teleop_screen, setupNavigationBar } from './Index/index_c_screen.js';
import { navigator_start_all } from './Index/index_d_navigator.js';
import { gamepad_socket, teleop_start_all } from './Index/index_e_teleop.js';
import { h264_start_all, h264_stop_all } from './Index/index_video_hlp.js';
import { mjpeg_start_all, mjpeg_stop_all } from './Index/index_video_mjpeg.js';
import { Router } from './router.js';

function initComponents() {
	try {
		[teleop_screen, socket_utils, dev_tools, page_utils].forEach((component) => component._init());
		$('#video_stream_type').val(page_utils.get_stream_type() === 'mjpeg' ? 'mjpeg' : 'h264');
		$('#message_box_button_take_control').click(() => gamepad_socket._request_take_over_control());
	} catch (error) {
		console.error('Error while initializing components:', error);
	}
}

function showHelp() {
	$('.showMessageButton').click(function () {
		$('.message_container').removeClass('hidden').hide().fadeIn(500);
		closeMessageContainer();
	});

	document.querySelector('.close_btn').addEventListener('click', function () {
		$('.message_container').hide();
		closeMessageContainer();
	});

	// Function to close the message container
	function closeMessageContainer() {
		$('#application_content').toggleClass('expanded');
		$('#header_bar').toggleClass('expanded');
	}

	// Event listener for clicks outside the message container
	$(document).mouseup(function (e) {
		var container = $('.message_container');
		if (container.is(':visible') && !container.is(e.target) && container.has(e.target).length === 0) {
			$('.message_container').hide();
			closeMessageContainer();
		}
	});
}

function start_all_handlers() {
	try {
		mjpeg_start_all();
		h264_start_all();
	} catch (error) {
		console.error('Error starting handlers:', error);
	}
}

function stop_all_handlers() {
	mjpeg_stop_all();
	h264_stop_all();
}

function handleVisibilityChange() {
	if (document.hidden) {
		stop_all_handlers();
	} else {
		start_all_handlers();
	}
}

function showSSID() {
	network_utils
		.getSSID()
		.then((ssid) => $('#header_bar #current_seg_name').text(ssid))
		.catch((error) => console.error('Failed to fetch SSID:', error));
}

$(window).on('load', () => {
	showSSID();
	['phone_controller_link'].forEach((id) => $(`#${id}`)[isMobileDevice() ? 'hide' : 'show']());

	let helpMessageManager = setupNavigationBar();
	const router = new Router(helpMessageManager);

	router.handleUserMenuRoute(localStorage.getItem('user.menu.screen') || 'settings_link');

	document.addEventListener('visibilitychange', handleVisibilityChange, false);
	$(window).on('focus', start_all_handlers);
	$(window).on('blur', stop_all_handlers);

	start_all_handlers();
	navigator_start_all();
	teleop_start_all();
});

export { initComponents, showHelp };
