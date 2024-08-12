import { addDataToMobileCommand } from './mobileController_c_logic.js';
import CTRL_STAT from './mobileController_z_state.js';

class AutoNavigationHandler {
	constructor() {}

	initializeDOM() {
		//TODO: it should hide the canvas but keep the squares visible
		const self = this; // Save the reference to 'this' (which is the class instance here)
		$('#mobile_controller_container .steeringWheel').hide();
		$('#mobile_controller_container .current_mode_button').show();
		$('.current_mode_text').hide();
		$('#mobile_controller_container .trail_canvas').hide();
		$('.rover_speed').css('display', 'flex');
		$('.control_symbol').css('display', 'flex');
		$('.autopilot_status').show();
		$('.autopilot_status').css('color', 'black');
		$('#mobile_controller_container #forward_square .square_text').text('increase max speed');
		$('#mobile_controller_container #backward_square .square_text').text('decrease max speed');
		$('#mobile_controller_container .current_mode_button').text('start');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
		$('#mobile_controller_container .current_mode_button').css('color', 'white');
		$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');

		$('#mobile_controller_container .current_mode_button').click(function () {
			const buttonText = $(this).text().toLowerCase();
			if (CTRL_STAT.currentPage == 'autopilot_link' && buttonText == 'start') {
				self.startAutoNavigation();
			}
			if (CTRL_STAT.currentPage == 'autopilot_link' && buttonText == 'stop') {
				self.stopAutoNavigation();
			}
		});

		document.querySelectorAll('.control_symbol').forEach((item) => {
			item.addEventListener('touchstart', (event) => {
				item.classList.add('active');
				const command = item.textContent.trim() === '+' ? 'increase' : 'decrease';
				this.handleSpeedControl(command); // 'this' now correctly refers to the instance of AutoNavigationHandler
			});
			item.addEventListener('touchend', () => {
				// Changed to arrow function
				item.classList.remove('active');
			});
		});
	}

	startAutoNavigation() {
		addDataToMobileCommand({ button_y: 1 });
		$('#mobile_controller_container .current_mode_button').text('stop');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
		$('#mobile_controller_container .current_mode_button').css('border', 'none');
	}

	stopAutoNavigation() {
		addDataToMobileCommand({ button_b: 1 });
		$('#mobile_controller_container .current_mode_button').text('start');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
		$('#mobile_controller_container .current_mode_button').css('color', 'white');
		$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
	}

	/**
	 * Send message to increase to decrease the autopilot mode
	 */
	handleSpeedControl(cmd) {
		// Update the speed display, ensuring it always has one decimal place
		if (cmd == 'increase') {
			addDataToMobileCommand({ arrow_up: 1 });
		} else if (cmd == 'decrease') {
			addDataToMobileCommand({ arrow_down: 1 });
		}
	}
}
var autoNavigationNavButtonHandler = new AutoNavigationHandler();
export { autoNavigationNavButtonHandler };
