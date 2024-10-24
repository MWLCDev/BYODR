import CTRL_STAT from '../mobileController_z_state.js';

class ConfidenceHandler {
	constructor() {
		this.confidenceWS = {};
	}

	initializeDOM() {
		$('body').addClass('confidence-feature');
		this.initializeConfidenceWS();
		this.bindButtonAction();
		this.mapFilename = null;
	}
	bindButtonAction() {
		$(' .current_mode_button').click(() => {
			if (CTRL_STAT.currentPage === 'map_recognition_link') {
				if (!$('body').hasClass('stop-mode') && !$('body').hasClass('return-mode') && !$('body').hasClass('map_recognition_loading-mode')) {
					// Start state
					this.sendSwitchConfidenceRequest('start_confidence');
					this.toggleButtonAppearance('show_stop_mode');
				} else if ($('body').hasClass('stop-mode')) {
					this.sendSwitchConfidenceRequest('stop_confidence');
					// The backend should respond with 'loading', which will trigger the loading state
				} else if ($('body').hasClass('return-mode')) {
					this.resetBodyClasses();
					// This will bring us back to the initial state
				}
			}
		});
	}

	sendSwitchConfidenceRequest(command) {
		if (this.confidenceWS.websocket && this.confidenceWS.websocket.readyState === WebSocket.OPEN) {
			this.confidenceWS.websocket.send(command);
		} else {
			console.error('Confidence websocket is not open. Command not sent. Attempting to reconnect...');
			this.checkAndReconnectWebSocket();
		}
	}

	resetBodyClasses() {
		$('body').removeClass('stop-mode map_recognition_loading-mode return-mode');
	}
	toggleButtonAppearance(cmd) {
		this.resetBodyClasses();
		if (cmd === 'show_stop_mode') {
			$('body').addClass('stop-mode');
		} else if (cmd === 'show_loading_mode') {
			$('body').addClass('map_recognition_loading-mode');
		} else if (cmd === 'show_return_mode') {
			$('body').addClass('return-mode');
		}
	}

	initializeConfidenceWS() {
		let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
		this.currentURL = `${document.location.protocol}`;
		let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/switch_confidence`;
		this.confidenceWS.websocket = new WebSocket(WSurl);

		this.confidenceWS.websocket.onopen = () => {
			this.confidenceWS.isWebSocketOpen = true;
		};

		this.confidenceWS.websocket.onmessage = (event) => {
			this.updateButtonState(event.data);
		};

		this.confidenceWS.websocket.onclose = () => {
			this.confidenceWS.isWebSocketOpen = false;
			setTimeout(() => this.checkAndReconnectWebSocket(), 500);
		};
	}

	checkAndReconnectWebSocket() {
		if (!this.confidenceWS.websocket || this.confidenceWS.websocket.readyState === WebSocket.CLOSED) {
			this.initializeConfidenceWS();
		}
	}

	loadMapIntoIframe(url) {
		const iframeSelector = '#map_frame, #top_layer_iframe';
		$(iframeSelector).attr('src', `${this.currentURL}/overview_confidence/${url}`);
	}
	updateButtonState(message) {
		try {
			if (message === 'loading') {
				this.toggleButtonAppearance('show_loading_mode');
			} else if (message.endsWith('.html')) {
				this.mapFilename = message.match(/[\w-]+\.html$/)[0];
				this.loadMapIntoIframe(this.mapFilename);
				this.toggleButtonAppearance('show_return_mode');
			}
		} catch (error) {
			console.error('Problem while changing the result from the backend:', error);
		}
	}
}

var confidenceNavButtonHandler = new ConfidenceHandler();
export { confidenceNavButtonHandler };
