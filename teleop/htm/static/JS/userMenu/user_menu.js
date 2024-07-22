var toggleBtn = document.getElementById('hamburger_menu_toggle');
var nav = document.querySelector('.hamburger_menu_nav');
var userMenu = document.getElementById('application-content');
var normalUI = document.getElementById('normal_ui');
var navLinks = document.querySelectorAll('.hamburger_menu_nav a'); // Select all nav links

// Function to toggle the sidebar and content blur

function toggleSidebar() {
	if (nav) nav.classList.toggle('active');
	if (normalUI) normalUI.classList.toggle('expanded');
	if (userMenu) userMenu.classList.toggle('expanded');
	if (toggleBtn) toggleBtn.classList.toggle('active');
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
		case 'controls':
			$('a#controls_link').addClass('active');
			menu_user_controls_main(el_container);
			break;
		case 'logbox':
			$('a#logbox_link').addClass('active');
			menu_user_logbox_main(el_container);
			break;
		default:
			$('a#settings_link').addClass('active');
			menu_user_settings_main(el_container);
	}
}

document.addEventListener('DOMContentLoaded', function () {
	// Set up the click handlers.
	$('a#home_link').click(function () {
		location = '/';
	});
	$('a#settings_link').click(function () {
		_user_menu_route_screen('settings');
	});
	$('a#controls_link').click(function () {
		_user_menu_route_screen('controls');
	});
	$('a#logbox_link').click(function () {
		_user_menu_route_screen('logbox');
	});

	// Load the last visited screen from cache. Default value for it is settings tab
	var screen = window.localStorage.getItem('user.menu.screen');
	if (screen == null) {
		screen = 'settings';
	}
	_user_menu_route_screen(screen);
});
