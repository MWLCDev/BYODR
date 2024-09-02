import { addDataToMobileCommand } from '../mobileController_c_logic.js';
import CTRL_STAT from '../mobileController_z_state.js';

class ManeuverTrainingHandler {
	constructor() {}

	initializeDOM() {
		// Add the class to enable maneuver training feature styles
		$('body').addClass('maneuver-training-feature');
		// Ensure the correct state is reflected (start/stop)
		this.updateTrainingState();

		this.bindButtonAction();
	}

	bindButtonAction() {
		$('#mobile_controller_container .F').click((event) => {
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
		$('body').addClass('training-started');
	}

	stopTraining() {
		addDataToMobileCommand({ button_b: 1 });
		$('body').removeClass('training-started');
	}

	updateTrainingState() {
		// Set the initial state of the button and styles
		if ($('body').hasClass('training-started')) {
			this.startTraining();
		} else {
			this.stopTraining();
		}
	}
}

var maneuverTrainingNavButtonHandler = new ManeuverTrainingHandler();
export { maneuverTrainingNavButtonHandler };
