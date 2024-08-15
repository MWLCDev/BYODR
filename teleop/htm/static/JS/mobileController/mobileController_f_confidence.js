import CTRL_STAT from './mobileController_z_state.js';
class ConfidenceHandler {
	constructor() {
		this.confidenceWS = {};
	}

	initializeDOM() {
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
		this.bindButtonAction();
	}

	bindButtonAction() {
		$('#mobile_controller_container .current_mode_button').click((event) => {
			const buttonText = $(event.target).text().toLowerCase();
			if (CTRL_STAT.currentPage == 'map_recognition_link' && buttonText == 'recognize') {
        this.sendSwitchConfidenceRequest('start_confidence');
				this.toggleButtonAppearance('stop');
			} else if (CTRL_STAT.currentPage == 'map_recognition_link' && buttonText == 'stop') {
				this.sendSwitchConfidenceRequest('stop_confidence');
				this.toggleButtonAppearance('start');
			} else if (CTRL_STAT.currentPage == 'map_recognition_link' && buttonText == 'return') {
				$('#mobile_controller_container #backward_square').show();
				$('#mobile_controller_container #forward_square').show();
				$('#map_frame').hide();
				this.toggleButtonAppearance('start');
			}
		});
	}

	/**
	 * Sends a command to the server via WebSocket.
	 * @param {string} command The command to be sent to the server.
	 */
	sendSwitchConfidenceRequest(command) {
		console.log(command);
		if (this.confidenceWS.websocket && this.confidenceWS.websocket.readyState === WebSocket.OPEN) {
			console.log(command);
			this.confidenceWS.websocket.send(command);
		} else {
			console.error('Confidence websocket is not open. Command not sent. Attempting to reconnect...');
			this.checkAndReconnectWebSocket();
		}
	}

	toggleButtonAppearance(cmd) {
		if (cmd == 'start') {
			$('#mobile_controller_container .current_mode_button').text('recognize');
			$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
			$('#mobile_controller_container .current_mode_button').css('color', 'white');
			$('#mobile_controller_container .current_mode_button').css('box-shadow', 'none');
		} else if (cmd == 'stop') {
			$('#mobile_controller_container .current_mode_button').text('stop');
			$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
			$('#mobile_controller_container .current_mode_button').css('border', 'none');
			$('#mobile_controller_container .square').children().show();
			$('.stop_text, .control_symbol').hide();
		} else if (cmd == 'return') {
			$('#mobile_controller_container .current_mode_button').text('return');
			$('#mobile_controller_container .current_mode_button').css('background-color', '#ffffff');
			$('#mobile_controller_container .current_mode_button').css('color', '#451c58');
			$('#mobile_controller_container .current_mode_button').css('border', '');
		} else if (cmd == 'show_result') {
			$('#mobile_controller_container .current_mode_button').show();
			$('#mobile_controller_container .current_mode_button').text('Show result');
			$('#mobile_controller_container .current_mode_button').css('border', 'none');
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

	loadMapIntoIframe(url) {
		$('#map_frame').attr('src', `${this.currentURL}/overview_confidence/${url}`).show();
	}
	/**
	 * Updates the button's appearance based on the received WebSocket message.
	 * @param {string} message The message received from the WebSocket.
	 */
	updateButtonState(message) {
		// console.log(message);
		if (message === 'loading') {
			$('#mobile_controller_container .current_mode_state').text('Loading...');
			$('#mobile_controller_container .current_mode_state').css('color', '#FF8A00');
			$('#mobile_controller_container .current_mode_button').hide();
		} else if (message.endsWith('.html')) {
			// Extract the filename from the message
			const filename = message.match(/[\w-]+\.html$/)[0];
			$('#mobile_controller_container .current_mode_state').hide();
			$('#mobile_controller_container #backward_square').hide();
			$('#mobile_controller_container #forward_square').hide();
			this.toggleButtonAppearance('show_result');

			$('#mobile_controller_container .current_mode_button')
				.off('click')
				.click(() => {
					// This will load the HTML content into the `forward_square` div without redirecting

					this.loadMapIntoIframe(filename);
					this.bindButtonAction();
					this.toggleButtonAppearance('return');
				});
		}
	}
}
var confidenceNavButtonHandler = new ConfidenceHandler();
export { confidenceNavButtonHandler };
