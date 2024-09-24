import { addDataToMobileCommand } from '../mobileController_c_logic.js';
import CTRL_STAT from '../mobileController_z_state.js';

class AutoNavigationHandler {
	constructor() {}

	initializeDOM() {
		$('body').addClass('auto-navigation-feature');
		this.updateNavigationState();
		this.bindButtonAction();
	}

	bindButtonAction() {
		$('#mobile_controller_container .current_mode_button').click(() => {
			console.log(CTRL_STAT.currentPage);
			if (CTRL_STAT.currentPage === 'auto_navigation_link') {
				if (!$('body').hasClass('navigation-started')) {
					this.startAutoNavigation();
				} else {
					this.stopAutoNavigation();
				}
			}
		});

		document.querySelectorAll('.control_symbol').forEach((item) => {
			item.addEventListener('click', (event) => {
				this.handleSymbolInteraction(item);
			});
		});
	}

	handleSymbolInteraction(item) {
		item.classList.add('active');
		const command = item.textContent.trim() === '+' ? 'increase' : 'decrease';
		this.handleSpeedControl(command);

		setTimeout(() => {
			item.classList.remove('active');
		}, 500); // Adjusted timing to match transition duration in mobileController.css
	}

	startAutoNavigation() {
		addDataToMobileCommand({ button_y: 1 });
		$('body').addClass('navigation-started');
	}

	stopAutoNavigation() {
		addDataToMobileCommand({ button_b: 1 });
		$('body').removeClass('navigation-started');
	}

	updateNavigationState() {
		// Set the initial state of the button and styles
		if ($('body').hasClass('navigation-started')) {
			this.startAutoNavigation();
		} else {
			this.stopAutoNavigation();
		}
	}

	handleSpeedControl(cmd) {
		if (cmd === 'increase') {
			addDataToMobileCommand({ arrow_up: 1 });
		} else if (cmd === 'decrease') {
			addDataToMobileCommand({ arrow_down: 1 });
		}
	}
}

var autoNavigationNavButtonHandler = new AutoNavigationHandler();
export { autoNavigationNavButtonHandler };
