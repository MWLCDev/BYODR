import { addDataToMobileCommand } from './mobileController_c_logic.js';
import CTRL_STAT from './mobileController_z_state.js';

class ManeuverTrainingHandler {
	constructor() {}

	initializeDOM() {
		//TODO: it should hide the canvas but keep the squares visible
		$('#mobile_controller_container .steeringWheel').hide();
		$('#mobile_controller_container #backward_square').children().hide();
		$('.control_symbol').css('display', 'none');
		$('#mobile_controller_container #backward_square .trail_canvas').hide();

		$('#mobile_controller_container #forward_square .square_text').text('forward');

		$('#mobile_controller_container .current_mode_button').show();
		$('#mobile_controller_container .current_mode_button').text('start');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
		$('#mobile_controller_container .current_mode_button').css('color', 'white');
		$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
		$('#mobile_controller_container #backward_square').addClass('maneuver_square');

		this.bindButtonAction();
	}
	bindButtonAction() {
		$('#mobile_controller_container .current_mode_button').click((event) => {
			const buttonText = $(event.target).text().toLowerCase();
			if (CTRL_STAT.currentPage === 'ai_training_link' && buttonText === 'start') {
				this.startTraining();
			}
			if (CTRL_STAT.currentPage === 'ai_training_link' && buttonText === 'stop') {
				this.stopTraining();
			}
		});
	}

	startTraining() {
		addDataToMobileCommand({ button_y: 1 });
		$('#mobile_controller_container .current_mode_button').text('stop');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
		$('#mobile_controller_container .current_mode_button').css('border', 'none');
	}

	stopTraining() {
		addDataToMobileCommand({ button_b: 1 });
		$('#mobile_controller_container .current_mode_button').text('start');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
		$('#mobile_controller_container .current_mode_button').css('color', 'white');
		$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
	}
}

var maneuverTrainingNavButtonHandler = new ManeuverTrainingHandler();
export { maneuverTrainingNavButtonHandler };
