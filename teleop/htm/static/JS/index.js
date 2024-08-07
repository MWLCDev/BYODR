import { dev_tools } from './Index/index_a_utils.js';
import { navigator_start_all, navigator_stop_all } from './Index/index_d_navigator.js';
import { teleop_start_all, teleop_stop_all } from './Index/index_e_teleop.js';
import { mjpeg_start_all, mjpeg_stop_all } from './Index/index_video_mjpeg.js';
import { h264_start_all, h264_stop_all } from './Index/index_video_hlp.js';

var hidden, visibilityChange;
if (typeof document.hidden !== 'undefined') {
	hidden = 'hidden';
	visibilityChange = 'visibilitychange';
} else if (typeof document.msHidden !== 'undefined') {
	hidden = 'msHidden';
	visibilityChange = 'msvisibilitychange';
} else if (typeof document.webkitHidden !== 'undefined') {
	hidden = 'webkitHidden';
	visibilityChange = 'webkitvisibilitychange';
}

function setupNavigationBar() {
	var toggleBtn = document.getElementById('hamburger_menu_toggle');
	var nav = document.querySelector('.hamburger_menu_nav');
	var userMenu = document.getElementById('application-content');
	var headerBar = document.getElementById('header_bar');
	var navLinks = document.querySelectorAll('.hamburger_menu_nav a');

	function toggleSidebar() {
		nav.classList.toggle('active');
		toggleBtn.classList.toggle('active');
		userMenu.classList.toggle('expanded');
		headerBar.classList.toggle('expanded');
	}

	toggleBtn.addEventListener('click', toggleSidebar);

	navLinks.forEach(function (link) {
		link.addEventListener('click', function () {
			toggleSidebar();
		});
	});

	document.addEventListener('click', function (event) {
		var isClickInsideNav = nav.contains(event.target);
		var isClickToggleBtn = toggleBtn.contains(event.target);

		if (!isClickInsideNav && !isClickToggleBtn && nav.classList.contains('active')) {
			toggleSidebar();
		}
	});
}

function start_all_handlers() {
	try {
		// const el_main_camera_display = document.getElementById('viewport_canvas');
		// console.log(el_main_camera_display.width, el_main_camera_display.height);
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
	if (document[hidden]) {
		stop_all_handlers();
	} else {
		start_all_handlers();
	}
}

window.addEventListener('load', function () {
	setupNavigationBar();
	if (!dev_tools.is_develop()) {
		window.history.pushState({}, '', '/');
	}
  
	document.addEventListener(visibilityChange, handleVisibilityChange, false);
	window.addEventListener('focus', start_all_handlers);
	window.addEventListener('blur', stop_all_handlers);
	navigator_start_all();
	teleop_start_all();
});
