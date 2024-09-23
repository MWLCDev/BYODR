import { addDataToMobileCommand } from '../mobileController_c_logic.js';
import CTRL_STAT from '../mobileController_z_state.js';

class ManeuverTrainingHandler {
	initializeDOM() {
		$('body').addClass('maneuver-training-feature');
		this.updateTrainingState();
		this.bindButtonAction();
	}

	bindButtonAction() {
		$('#mobile_controller_container .current_mode_button').click(() => {
			if (CTRL_STAT.currentPage === 'ai_training_link') {
				if (!$('body').hasClass('training-started')) {
					this.startTraining();
				} else {
					this.stopTraining();
				}
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
