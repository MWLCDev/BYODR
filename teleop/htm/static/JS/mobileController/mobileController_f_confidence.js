import CTRL_STAT from './mobileController_z_state.js';
class ConfidenceHandler {
	constructor() {
		this.confidenceWS = {};
	}

	initializeDOM() {
		$('.current_mode_text').show();
		$('.current_mode_text').css('text-align', 'center');
		$('#mobile_controller_container .steeringWheel').hide();
		$(' .current_mode_button').show();
		$('#mobile_controller_container .square').children().show();
		$('.control_symbol').css('display', 'none');
		$('.stop_text').css('display', 'none');
		$('#mobile_controller_container #forward_square .square_text').text('forward');
		$('#mobile_controller_container #backward_square .square_text').text('backward');

		$('.current_mode_button').text('recognize');
		$('.current_mode_button').css('background-color', '#451c58');
		$('.current_mode_button').css('color', 'white');
		$('.current_mode_button').css('box-shadow', 'none');
		this.initializeConfidenceWS();
		this.bindButtonAction();
	}

	bindButtonAction() {
		$('.current_mode_button').click((event) => {
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
				$('#map_frame, #top_layer_iframe').hide();
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
			$('.current_mode_button').text('recognize');
			$('.current_mode_button').css('background-color', '#451c58');
			$('.current_mode_button').css('color', 'white');
			$('.current_mode_button').css('box-shadow', 'none');
		} else if (cmd == 'stop') {
			$('.current_mode_button').text('stop');
			$('.current_mode_button').css('background-color', '#f41e52');
			$('.current_mode_button').css('border', 'none');
			$('#mobile_controller_container .square').children().show();
			$('.stop_text, .control_symbol').hide();
		} else if (cmd == 'return') {
			$('.current_mode_button').text('return');
			$('.current_mode_button').css('background-color', '#ffffff');
			$('.current_mode_button').css('color', '#451c58');
			$('.current_mode_button').css('border', '');
		} else if (cmd == 'show_result') {
			$('.current_mode_button').show();
			$('.current_mode_button').text('Show result');
			$('.current_mode_button').css('border', 'none');
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
    const iframeSelector = '#map_frame, #top_layer_iframe';

    // Set the source of the iframe
    $(iframeSelector).attr('src', `${this.currentURL}/overview_confidence/${url}`);

    // Fade in the iframe when the content is ready to display
    $(iframeSelector).fadeIn(500); // 500ms for the fade-in effect
}

	/**
	 * Updates the button's appearance based on the received WebSocket message.
	 * @param {string} message The message received from the WebSocket.
	 */
	updateButtonState(message) {
		// console.log(message);
		if (message === 'loading') {
			$('.current_mode_state').text('Loading...');
			$('.current_mode_state').css('color', '#FF8A00');
			$('.current_mode_button').hide();
		} else if (message.endsWith('.html')) {
			// Extract the filename from the message
			const filename = message.match(/[\w-]+\.html$/)[0];
			$('.current_mode_state').hide();
			$('#mobile_controller_container #backward_square').hide();
			$('#mobile_controller_container #forward_square').hide();
			this.toggleButtonAppearance('show_result');

			$('.current_mode_button')
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
