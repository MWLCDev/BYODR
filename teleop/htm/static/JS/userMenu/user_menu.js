import { initializeSettings } from './menu_settings.js';
import { fetchData } from './menu_logbox.js';
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

	// Use the main element directly
	const el_container = $('main#application-content');
	el_container.empty(); // Clear the existing content

	// Save the last visited screen in the cache
	window.localStorage.setItem('user.menu.screen', screen);

	switch (screen) {
		case 'home_link':
			$('a#home_link').addClass('active');
			el_container.load('/normal_ui');
			break;
		case 'settings_link':
			$('a#settings_link').addClass('active');
			el_container.load('/menu_settings', initializeSettings); // Initialize settings after load
			break;
		case 'controls_link':
			$('a#controls_link').addClass('active');
			el_container.load('/menu_controls');
			break;
		case 'events_link':
			$('a#events_link').addClass('active');
			el_container.load('/menu_logbox', fetchData); // Fetch data after load
			break;
		case 'phone_controller_link':
			$('a#phone_controller_link').addClass('active');
			el_container.load('/mc');
			break;
	}
}

async function getSSID() {
	try {
		const response = await fetch('/run_get_SSID');
		const data = await response.text();
		return data;
	} catch (error) {
		console.error('Error fetching SSID for current robot:', error);
	}
}
document.addEventListener('DOMContentLoaded', function () {
	// Set up the click handlers for menu navigation
	$('a#home_link, a#settings_link, a#controls_link, a#events_link, a#phone_controller_link').click(function () {
		_user_menu_route_screen(this.id);
	});
	// Correctly handle the promise returned by getSSID
	getSSID()
		.then((ssid) => {
			$('#header_bar #current_seg_name').text(ssid);
		})
		.catch((error) => {
			console.error('Failed to fetch SSID:', error);
		});
	// Load the last visited screen from cache or default to 'settings'
	var screen = window.localStorage.getItem('user.menu.screen') || 'settings_link';
	_user_menu_route_screen(screen);
});
