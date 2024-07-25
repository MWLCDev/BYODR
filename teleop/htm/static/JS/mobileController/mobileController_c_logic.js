import CTRL_STAT from './mobileController_z_state.js';

function initializeWS() {
	let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
	let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
	CTRL_STAT.websocket = new WebSocket(WSurl);

	CTRL_STAT.websocket.onopen = function (event) {
		console.log('Mobile controller (WS) connection opened');
		addKeyToSentCommand('button_b', 1);
		CTRL_STAT.stateErrors = '';
	};

	// Check the respond from the endpoint. If the user is operator or viewer
	// if it is a viewer, then refresh
	CTRL_STAT.websocket.onmessage = function (event) {
		let parsedData = JSON.parse(event.data); // The received data is in string, so I need to convert to JSON
		if (parsedData['control'] == 'operator') {
			//Place holder until implementation with multi segment is over
		} else if (parsedData['control'] == 'viewer') {
			CTRL_STAT.stateErrors = 'controlError';
			// redraw(undefined, true, true, false);
		}
	};

	CTRL_STAT.websocket.onerror = function (error) {
		console.log('WebSocket Error:', error);
	};

	CTRL_STAT.websocket.onclose = function (event) {
		console.log('Mobile controller (WS) connection closed');
		CTRL_STAT.stateErrors = 'connectionError';
		// redraw(undefined, true, true, false);
	};
}

function setStatistics(x, y, getInferenceState) {
	CTRL_STAT.throttleSteeringJson = {
		throttle: Number(y),
		steering: Number(x),
		mobileInferenceState: getInferenceState,
	};
}

/** Function to add a temporary key-value pair to the sent command through mobile controller socket */
function addKeyToSentCommand(key, value) {
	CTRL_STAT.throttleSteeringJson[key + '_temp'] = value;
}
// Variable to store the last data sent
let lastSentData = {};

function sendJSONCommand() {
	if (CTRL_STAT.websocket && CTRL_STAT.websocket.readyState === WebSocket.OPEN) {
		// Create a copy of the data to send, removing '_temp' from temporary keys
		const dataToSend = {};
		for (const key in CTRL_STAT.throttleSteeringJson) {
			if (key.endsWith('_temp')) {
				const originalKey = key.slice(0, -5); // Remove last 5 characters ('_temp')
				dataToSend[originalKey] = CTRL_STAT.throttleSteeringJson[key];
			} else {
				dataToSend[key] = CTRL_STAT.throttleSteeringJson[key];
			}
		}

		// Check if the current data to send is different from the last sent data
		const dataToSendString = JSON.stringify(dataToSend);
		if (JSON.stringify(lastSentData) !== dataToSendString) {
			CTRL_STAT.websocket.send(dataToSendString);

			// Update last sent data
			lastSentData = dataToSend;
		}

		// Clean up temporary keys
		Object.keys(CTRL_STAT.throttleSteeringJson).forEach((key) => {
			if (key.endsWith('_temp')) {
				delete CTRL_STAT.throttleSteeringJson[key];
			}
		});
	}

	// Continue to attempt sending data every 100 milliseconds
	setTimeout(sendJSONCommand, 100);
}

export { addKeyToSentCommand, setStatistics, initializeWS, sendJSONCommand };
