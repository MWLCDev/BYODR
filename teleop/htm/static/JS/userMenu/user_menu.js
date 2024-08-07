import { initializeSettings } from './menu_settings.js';
import { LogBox } from './menu_logbox.js';
// TODO: rename this file
var toggleBtn = document.getElementById('hamburger_menu_toggle');
var nav = document.querySelector('.hamburger_menu_nav');
var userMenu = document.getElementById('application-content');
var headerBar = document.getElementById('header_bar');
var navLinks = document.querySelectorAll('.hamburger_menu_nav a'); // Select all nav links

// Function to toggle the sidebar and content blur

function toggleSidebar() {
	nav.classList.toggle('active');
	toggleBtn.classList.toggle('active');
	userMenu.classList.toggle('expanded');
	headerBar.classList.toggle('expanded');
	console.log('found all');
}

if (toggleBtn) {
	toggleBtn.addEventListener('click', toggleSidebar);
}

navLinks.forEach(function (link) {
	link.addEventListener('click', function () {
		// Hide the sidebar
		toggleSidebar();
	});
});

// Event listener for clicking outside the sidebar to close it
document.addEventListener('click', function (event) {
	var isClickInsideNav = nav.contains(event.target);
	var isClickToggleBtn = toggleBtn.contains(event.target);

	if (!isClickInsideNav && !isClickToggleBtn && nav.classList.contains('active')) {
		toggleSidebar();
	}
});

function _user_menu_route_screen(screen) {
	$('.hamburger_menu_nav a').each(function () {
		$(this).removeClass('active');
	});

	const el_parent = $('main.application-content');
	const el_container = $('<div/>', { id: 'application-content-container' });
	el_parent.find('div#application-content-container').remove();
	el_parent.append(el_container);
	// Save the last visited screen in the cache
	window.localStorage.setItem('user.menu.screen', screen);
	switch (screen) {
		case 'home_link':
			$('a#home_link').addClass('active');
			$('#application-content-container').load('/normal_ui', function () {});
			break;
		case 'settings_link':
			$('a#settings_link').addClass('active');
			$('#application-content-container').load('/menu_settings', function () {});
			initializeSettings();
			break;
		case 'controls_link':
			$('a#controls_link').addClass('active');
			$('#application-content-container').load('/menu_controls', function () {});
			break;
		case 'events_link':
			$('a#events_link').addClass('active');
			$('#application-content-container').load('/menu_logbox', function () {
				const logBox = new LogBox();
				logBox.init();
			});
			break;
		case 'phone_controller_link':
			$('a#phone_controller_link').addClass('active');
			$('#application-content-container').load('/mc', function () {});
			break;
	}
}

document.addEventListener('DOMContentLoaded', function () {
	// Set up the click handlers.
	$('a#home_link').click(function () {
		_user_menu_route_screen('home_link');
	});
	$('a#settings_link').click(function () {
		_user_menu_route_screen('settings_link');
	});
	$('a#controls_link').click(function () {
		_user_menu_route_screen('controls_link');
	});
	$('a#events_link').click(function () {
		_user_menu_route_screen('events_link');
	});
	$('a#phone_controller_link').click(function () {
		_user_menu_route_screen('phone_controller_link');
	});

	// Load the last visited screen from cache. Default value for it is settings tab
	var screen = window.localStorage.getItem('user.menu.screen');
	if (screen == null) {
		screen = 'settings';
	}
	_user_menu_route_screen(screen);
});
