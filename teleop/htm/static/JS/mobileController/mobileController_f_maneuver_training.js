class ManeuverTrainingHandler {
	constructor() {}
	initializeDOM() {
		$('#mobile_controller_container .steeringWheel').hide();
		$('#mobile_controller_container .current_mode_button').show();
		$('#mobile_controller_container .current_mode_button').text('stop');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
		$('#mobile_controller_container .current_mode_button').css('border', 'none');
		$('#mobile_controller_container .current_mode_text').text('ai training');
		$('#mobile_controller_container #backward_square').hide();
	}

	handleInferenceTrainClick() {
		this._inferenceState = this._inferenceState === 'train' ? 'true' : 'train';
		if (this._inferenceState === 'train') {
			this.startTraining();
		} else {
			this.stopTraining();
		}
	}

	startTraining() {
		this.inferenceTrainingButton.innerText = 'Stop Training';
		addKeyToSentCommand('button_y', 1);
		this.hideOptionsButton.innerText = 'Go to manual mode';
		this.InferenceAutoNavigationToggle.style.display = 'none';
	}

	stopTraining() {
		this.inferenceTrainingButton.innerText = 'Start Training';
		$('#mobile_controller_container .square').hide();
		addKeyToSentCommand('button_b', 1);
		this.hideOptionsButton.innerText = 'Hide Options';
		this.InferenceAutoNavigationToggle.style.display = 'flex';
	}
}

var maneuverTrainingNavButtonHandler = new ManeuverTrainingHandler();
export { maneuverTrainingNavButtonHandler };
