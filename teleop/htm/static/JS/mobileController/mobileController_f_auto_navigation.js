import { server_socket } from '../Index/index_e_teleop.js';

class AutoNavigationToggleButton {
	constructor() {
		this.logWS = {}; // Placeholder for WebSocket.
		this.logWSmessage;
		this.autoReconnectInterval = 9000;
		// this.initializeLogWS();
		/*
    Means no smoothing for the other classes
     false == working on normal mode
     true == Inference is working on mobile controller 
     train == Inference is on training mode
     auto == Inference is on auto mode
    */
		this._inferenceState = 'false';
		this.currentAutoSpeed = 0;
		// this.buttonsEventListener();
		// server_socket.add_server_message_listener(function (message) {
		// 	this.decorate_server_message(message);
		// });
	}

	initializeDOM() {
		console.log('first');
		$('#mobile_controller_container .steeringWheel').hide();
		$('#mobile_controller_container .current_mode_button').show();
		$('#mobile_controller_container .current_mode_button').text('stop');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
		$('#mobile_controller_container .current_mode_button').css('border', 'none');
    $("#mobile_controller_container #forward_square .square_text").text("increase max speed")
    $("#mobile_controller_container #backward_square .square_text").text("decrease max speed")
	}

	get getInferenceState() {
		return this._inferenceState;
	}

	buttonsEventListener() {
		this.toggleButton.addEventListener('click', () => this.showInferenceOptions());
		this.hideOptionsButton.addEventListener('click', () => this.hideInferenceOptions());
		this.inferenceTrainingButton.addEventListener('click', () => this.handleInferenceTrainClick());
		this.InferenceAutoNavigationToggle.addEventListener('click', () => this.handleAutoNavigationClick());
	}

	hideInferenceOptions() {
		this.InferenceAutoSpeedText.style.display = 'none';
		this.optionsContainer.style.display = 'none';
		this.toggleButtonContainer.style.display = 'flex';
		// Switch to driver_mode.teleop.direct mode
		addKeyToSentCommand('button_b', 1);
		// Turn off all the buttons to start state
		if (this._inferenceState == 'auto') {
			this.handleAutoNavigationClick();
			this._inferenceState = 'false';
		} else if (this._inferenceState == 'train') {
			this.handleInferenceTrainClick();
			this._inferenceState = 'false';
		}
		//Make it start with dark colour
		redraw(undefined, true, true, true);
		this._inferenceState = 'false';
	}

	showInferenceOptions() {
		$('#mobile_controller_container .square').hide();
		this.optionsContainer.style.display = 'flex';
		this.toggleButtonContainer.style.display = 'none';
		this._inferenceState = 'true';
	}

	handleAutoNavigationClick() {
		this._inferenceState = this._inferenceState === 'auto' ? 'true' : 'auto';
		// Now decide what to do based on the new state
		if (this._inferenceState === 'auto') {
			this.startAutoNavigation();
		} else {
			this.stopAutoNavigation();
		}
	}

	startAutoNavigation() {
		this.InferenceAutoNavigationToggle.innerText = 'Stop Auto-navigation';
		redraw(undefined, true, true, false);
		addKeyToSentCommand('button_y', 1);
		$('#mobile_controller_container #forward_square').text('increase speed');
		$('#mobile_controller_container #forward_square').text('decrease speed');
		this.InferenceAutoSpeedText.style.display = 'block';
		this.hideOptionsButton.innerText = 'Go to manual mode';
		this.inferenceTrainingButton.style.display = 'none';
	}

	stopAutoNavigation() {
		this.InferenceAutoNavigationToggle.innerText = 'Start Auto-navigation';
		$('#mobile_controller_container .square').hide();
		addKeyToSentCommand('button_b', 1);
		this.InferenceAutoSpeedText.style.display = 'none';
		this.inferenceTrainingButton.style.display = 'flex';
		this.hideOptionsButton.innerText = 'Hide Options';
		this.speedElement.innerHTML = `0 Km/h`;
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
		redraw(undefined, true, false, true);
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

	/**
	 * Send message to increase to decrease the autopilot mode
	 * @param {string} touchedTriangle - name of the triangle selected
	 */
	handleSpeedControl(touchedTriangle) {
		// Retrieve the current speed from the element
		// Round the received number to the nearest 0.5 for consistency
		let roundedSpeed = Math.round(this.logWSmessage.max_speed * 2) / 2;
		if (!this.logWSmessage._is_on_autopilot) {
			addKeyToSentCommand('button_y', 1);
			console.log(this.logWSmessage._is_on_autopilot);
		}
		// Update the speed display, ensuring it always has one decimal place
		this.speedElement.innerHTML = `${roundedSpeed.toFixed(1)} Km/h`;
		if (touchedTriangle == 'top' && roundedSpeed < 6) {
			addKeyToSentCommand('arrow_up', 1);
		} else if (touchedTriangle == 'bottom' && roundedSpeed > 0) {
			addKeyToSentCommand('arrow_down', 1);
		}
	}

	/**
	 * Add fields related to INF state to the message
	 * @param {json} message Message received from log endpoint
	 */
	decorate_server_message(message) {
		message._is_on_autopilot = message.ctl == 5;
		message._has_passage = message.inf_total_penalty < 1;
		if (message.geo_head == undefined) {
			message.geo_head_text = 'n/a';
		} else {
			message.geo_head_text = message.geo_head.toFixed(2);
		}
		this.logWSmessage = message;
	}

	checkAndReconnectWebSocket() {
		if (!this.logWS.websocket || this.logWS.websocket.readyState === WebSocket.CLOSED) {
			this.initializeLogWS();
		}
	}
}
var autoNavigationToggleButton = new AutoNavigationToggleButton();
export { autoNavigationToggleButton };
