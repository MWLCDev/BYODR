import CTRL_STAT from './mobileController_z_state.js';
class ConfidenceHandler {
	constructor() {
		this.confidenceWS = {};
	}

	initializeDOM() {
		const self = this; // Save the reference to 'this' (which is the class instance here)

		$('.current_mode_text').show();
		$('.current_mode_text').css('text-align', 'center');
		$('#mobile_controller_container .steeringWheel').hide();
		$('#mobile_controller_container .current_mode_button').show();
		$('#mobile_controller_container .square').children().show();
		$('.control_symbol').css('display', 'none');
		$('.stop_text').css('display', 'none');
		$('#mobile_controller_container #forward_square .square_text').text('forward');
		$('#mobile_controller_container #backward_square .square_text').text('backward');

		$('#mobile_controller_container .current_mode_button').text('recognize');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
		$('#mobile_controller_container .current_mode_button').css('color', 'white');
		$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
		this.initializeConfidenceWS();
		$('#mobile_controller_container .current_mode_button').click(function () {
			const buttonText = $(this).text().toLowerCase();
			if (CTRL_STAT.currentPage == 'map_recognition_link' && buttonText == 'recognize') {
				self.sendSwitchConfidenceRequest('start_confidence');
				self.toggleButtonAppearance('start');
			}
			if (CTRL_STAT.currentPage == 'map_recognition_link' && buttonText == 'stop') {
				self.sendSwitchConfidenceRequest('stop_confidence');
				self.toggleButtonAppearance('stop');
			}
		});
	}

	/**
	 * Sends a command to the server via WebSocket.
	 * @param {string} command The command to be sent to the server.
	 */
	sendSwitchConfidenceRequest(command) {
		if (this.confidenceWS.websocket && this.confidenceWS.websocket.readyState === WebSocket.OPEN) {
			this.confidenceWS.websocket.send(command);
		} else {
			console.error('Confidence websocket is not open. Command not sent. Attempting to reconnect...');
			this.checkAndReconnectWebSocket();
		}
	}

	toggleButtonAppearance(cmd) {
		if (cmd == 'start') {
			$('#mobile_controller_container .current_mode_button').text('stop');
			$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
			$('#mobile_controller_container .current_mode_button').css('border', 'none');
			$('#mobile_controller_container .square').children().show();
		} else {
			$('#mobile_controller_container .current_mode_button').text('recognize');
			$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
			$('#mobile_controller_container .current_mode_button').css('color', 'white');
			$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
		}
	}

	/**
	 * Initializes the WebSocket connection for real-time data updates and sets up event listeners.
	 */
	initializeConfidenceWS() {
		let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
		this.currentURL = `${document.location.protocol}`;
		let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/switch_confidence`;
		this.confidenceWS.websocket = new WebSocket(WSurl);

		this.confidenceWS.websocket.onopen = (event) => {
			this.confidenceWS.isWebSocketOpen = true;
		};

		this.confidenceWS.websocket.onmessage = (event) => {
			this.updateButtonState(event.data);
		};

		this.confidenceWS.websocket.onclose = (event) => {
			console.log('Confidence websocket connection closed');
			this.confidenceWS.isWebSocketOpen = false;
			// Automatically try to reconnect after a specified interval
			setTimeout(() => this.checkAndReconnectWebSocket(), 500);
		};
	}

	/**
	 * Checks the WebSocket's current state and attempts to reconnect if it's closed.
	 */
	checkAndReconnectWebSocket() {
		if (!this.confidenceWS.websocket || this.confidenceWS.websocket.readyState === WebSocket.CLOSED) {
			this.initializeConfidenceWS();
		}
	}

	/**
	 * Updates the button's appearance based on the received WebSocket message.
	 * @param {string} message The message received from the WebSocket.
	 */
	updateButtonState(message) {
		if (message === 'loading') {
			this.toggleButton.innerHTML = 'Loading...';
			this.toggleButton.disabled = true;
		} else if (message.endsWith('.html')) {
			// Extract the filename from the message
			const filename = message.match(/[\w-]+\.html$/)[0];

			this.toggleButton.innerHTML = 'View Results';
			this.toggleButton.disabled = false;
			this.toggleButton.onclick = () => {
				window.location.href = `${this.currentURL}/overview_confidence/${filename}`;
			};
		}
	}
}
var confidenceNavButtonHandler = new ConfidenceHandler();
export { confidenceNavButtonHandler };
