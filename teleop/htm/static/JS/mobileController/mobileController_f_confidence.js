/**
 * Handles toggle button interactions and manages WebSocket connections for real-time data updates.
 */
class ConfidenceHandler {
	constructor() {
		this.confidenceWS = undefined;
	}

	initializeDOM() {
		$('#mobile_controller_container .current_mode_text').text('map recognize');
		$('#mobile_controller_container .current_mode_text').css('text-align', 'center');
		$('#mobile_controller_container .steeringWheel').hide();
		$('#mobile_controller_container .current_mode_button').show();
		$('#mobile_controller_container .current_mode_button').text('recognize');
		$('#mobile_controller_container .current_mode_button').css('background-color', '#451c58');
		$('#mobile_controller_container .current_mode_button').css('color', 'white');
		this.initializeConfidenceWS();
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
