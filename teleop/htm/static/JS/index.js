import { dev_tools, page_utils, socket_utils, network_utils } from './Index/index_a_utils.js';
import { teleop_screen } from './Index/index_c_screen.js';
import { navigator_start_all } from './Index/index_d_navigator.js';
import { gamepad_socket, teleop_start_all } from './Index/index_e_teleop.js';
import { h264_start_all, h264_stop_all } from './Index/index_video_hlp.js';
import { mjpeg_start_all, mjpeg_stop_all } from './Index/index_video_mjpeg.js';
import { assignNavButtonActions } from './mobileController/mobileController_a_app.js';
import { handleUserMenuRoute, updateHeaderBar } from './router.js';

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
		$('.messageContainer').removeClass('hidden').hide().fadeIn(500);
		$('#application-content').addClass('expanded');
		$('#header_bar').addClass('expanded');
	});

	document.querySelector('.close-btn').addEventListener('click', function () {
		closeMessageContainer();
	});

	// Function to close the message container
	function closeMessageContainer() {
		$('.messageContainer').hide();
		$('#application-content').removeClass('expanded');
		$('#header_bar').removeClass('expanded');
	}

	// Event listener for clicks outside the message container
	$(document).mouseup(function (e) {
		var container = $('.messageContainer');
		if (!container.is(e.target) && container.has(e.target).length === 0) {
			closeMessageContainer();
		}
	});
}

function setupNavigationBar() {
	const toggleBtn = $('#hamburger_menu_toggle');
	const nav = $('.hamburger_menu_nav');
	const userMenu = $('#application-content');
	const headerBar = $('#header_bar');

	const toggleSidebar = () => {
		nav.toggleClass('active');
		toggleBtn.toggleClass('active');
		userMenu.toggleClass('expanded');
		headerBar.toggleClass('expanded');
	};

	toggleBtn.click(toggleSidebar);

	nav.find('a').click(toggleSidebar);

	$(document).click((event) => {
		if (!nav.is(event.target) && !toggleBtn.is(event.target) && nav.hasClass('active')) {
			toggleSidebar();
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

$(window).on('load', () => {
	$('.hamburger_menu_nav a').click(function () {
		handleUserMenuRoute(this.id);
		assignNavButtonActions(this.id);
	});

	network_utils
		.getSSID()
		.then((ssid) => $('#header_bar #current_seg_name').text(ssid))
		.catch((error) => console.error('Failed to fetch SSID:', error));

	updateHeaderBar();
	handleUserMenuRoute(localStorage.getItem('user.menu.screen') || 'settings_link');
	setupNavigationBar();

	if (!dev_tools.is_develop()) {
		window.history.pushState({}, '', '/');
	}

	document.addEventListener('visibilitychange', handleVisibilityChange, false);
	$(window).on('focus', start_all_handlers);
	$(window).on('blur', stop_all_handlers);

	start_all_handlers();
	navigator_start_all();
	teleop_start_all();
});

export { initComponents, showHelp };
