import CTRL_STAT from '../mobileController_z_state.js';

class ConfidenceHandler {
	constructor() {
		this.confidenceWS = {};
	}

	initializeDOM() {
		$('body').addClass('confidence-feature');
		this.toggleButtonAppearance('start');
		this.initializeConfidenceWS();
		this.bindButtonAction();
	}

	bindButtonAction() {
		$('#mobile_controller_container .current_mode_button').click(() => {
			if (CTRL_STAT.currentPage === 'map_recognition_link') {
				// If no mode-related class is present, we start recognizing
				if (!$('body').hasClass('recognize-mode') && !$('body').hasClass('stop-mode') && !$('body').hasClass('return-mode') && !$('body').hasClass('show-result-mode')) {
					// Start recognition process
					this.sendSwitchConfidenceRequest('start_confidence');
					this.toggleButtonAppearance('stop');
				} else if ($('body').hasClass('recognize-mode')) {
					// Stop the recognition process
					this.sendSwitchConfidenceRequest('stop_confidence');
					this.toggleButtonAppearance('start');
				} else if ($('body').hasClass('stop-mode')) {
					// Return to initial state and hide the map if needed
					this.toggleButtonAppearance('start');
					$('#map_frame, #top_layer_iframe').hide();
				}
			}
		});
	}

	sendSwitchConfidenceRequest(command) {
		console.log(command);
		if (this.confidenceWS.websocket && this.confidenceWS.websocket.readyState === WebSocket.OPEN) {
			this.confidenceWS.websocket.send(command);
		} else {
			console.error('Confidence websocket is not open. Command not sent. Attempting to reconnect...');
			this.checkAndReconnectWebSocket();
		}
	}

	toggleButtonAppearance(cmd) {
		$('body').removeClass('recognize-mode stop-mode return-mode show-result-mode');

		if (cmd == 'start') {
			$('body').addClass('recognize-mode');
		} else if (cmd == 'stop') {
			$('body').addClass('stop-mode');
		} else if (cmd == 'return') {
			$('body').addClass('return-mode');
		} else if (cmd == 'show_result') {
			$('body').addClass('show-result-mode');
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
			console.log('Confidence websocket connection closed');
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
		$(iframeSelector).attr('src', `${this.currentURL}/overview_confidence/${url}`).fadeIn(500);
	}

	updateButtonState(message) {
		if (message === 'loading') {
			$('body').addClass('loading-mode').removeClass('show-result-mode');
		} else if (message.endsWith('.html')) {
			const filename = message.match(/[\w-]+\.html$/)[0];
			this.toggleButtonAppearance('show_result');

			$('.current_mode_button')
				.off('click')
				.click(() => {
					this.loadMapIntoIframe(filename);
					this.toggleButtonAppearance('return');
				});
		}
	}
}

var confidenceNavButtonHandler = new ConfidenceHandler();
export { confidenceNavButtonHandler };
