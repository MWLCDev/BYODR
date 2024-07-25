import { bottomTriangle, topTriangle } from './mobileController_b_shape_triangle.js';
import CTRL_STAT from './mobileController_z_state.js';

function initializeWS() {
	let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
	let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
	CTRL_STAT.websocket = new WebSocket(WSurl);

	CTRL_STAT.websocket.onopen = function (event) {
		console.log('Mobile controller (WS) connection opened');
		addKeyToSentCommand('button_b', 1);
		CTRL_STAT.stateErrors = '';
		CTRL_STAT.isWebSocketOpen = true;
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
		CTRL_STAT.isWebSocketOpen = false; // Reset the flag when WebSocket is closed
	};
}

/**
 * Calculate and set differences in y coordinate relative to the screen's center,
 * effectively determining the position and movement of the control dot relative to the triangle tip.
 * @param {number} user_touch_X - X position of the user's touch input.
 */
function deltaCoordinatesFromTip(user_touch_X) {
	let relativeX = user_touch_X - window.innerWidth / 2;
	return relativeX;
}

function SetStatistics(user_touch_X, user_touch_Y, y, getInferenceState) {
	let shapeHeight = window.innerHeight / 4; //It is the same value as in updateDimensions()=> this.height
	CTRL_STAT.throttleSteeringJson = {
		throttle: -y.toFixed(3),
		steering: Number((user_touch_X / (shapeHeight / Math.sqrt(3))).toFixed(3)),
		mobileInferenceState: getInferenceState,
	};
}

/**
 * Handles the movement of the dot within specified triangle boundaries.
 * @param {number} touchX - X position of the touch.
 * @param {number} touchY - Y position of the touch.
 * @param {*} getInferenceState - Function to get the current inference state.
 */
function handleDotMove(touchX, touchY, getInferenceState) {
	// Determine the triangle and its vertical boundaries based on the selection.
	const isTopTriangle = CTRL_STAT.selectedTriangle === 'top';
	const triangle = isTopTriangle ? topTriangle : bottomTriangle;
	const midScreen = window.innerHeight / 2;

	// Calculate minY and maxY based on the mode.
	let minY, maxY;
	if (getInferenceState === 'auto') {
		minY = isTopTriangle ? midScreen - triangle.height : midScreen;
		maxY = isTopTriangle ? midScreen : midScreen + triangle.height;
	} else {
		minY = isTopTriangle ? CTRL_STAT.midScreen - triangle.height : CTRL_STAT.midScreen;
		maxY = isTopTriangle ? CTRL_STAT.midScreen : CTRL_STAT.midScreen + triangle.height;
	}

	// Constrain the Y position within the triangle's boundaries.
	let y = Math.max(minY, Math.min(touchY, maxY));

	// Calculate the relative Y position within the triangle.
	// This is initialized here to ensure it has a value in all code paths.
	let relativeY = (y - (getInferenceState === 'auto' ? midScreen : CTRL_STAT.midScreen)) / triangle.height;

	let deadZoneSlider = document.getElementById('deadZoneWidth');
	let savedDeadZoneWidth = getSavedDeadZoneWidth();
	deadZoneSlider.value = savedDeadZoneWidth; // Set the slider to the saved value
	let deadZoneWidth = window.innerWidth * parseFloat(savedDeadZoneWidth);

	let deadZoneMinX = window.innerWidth / 2 - deadZoneWidth / 2;
	let deadZoneMaxX = window.innerWidth / 2 + deadZoneWidth / 2;
	let inDeadZone = touchX >= deadZoneMinX && touchX <= deadZoneMaxX;

	// Modify the logic to handle the X position considering the dead zone
	let xOfDot;

	if (inDeadZone) {
		xOfDot = window.innerWidth / 2;
		relativeY = (y - CTRL_STAT.midScreen) / triangle.height; // Default value when in dead zone, adjust as necessary
	} else {
		let maxXDeviation = Math.abs(relativeY) * (triangle.baseWidth / 2);
		xOfDot = Math.max(Math.min(touchX, window.innerWidth / 2 + maxXDeviation), window.innerWidth / 2 - maxXDeviation);
	}

	// Update the dot's position.
	// cursorFollowingDot.setPosition(xOfDot, y);
	if (inDeadZone) {
		SetStatistics(0, y, relativeY, getInferenceState);
	} else if (getInferenceState !== 'auto') {
		let relative_x = 0;
		SetStatistics(relative_x, touchY, relativeY, getInferenceState);
	}
}

/**
 * Function to add a temporary key-value pair to the sent command through mobile controller socket
 * @param {string} key
 * @param {string} value
 */
function addKeyToSentCommand(key, value) {
	CTRL_STAT.throttleSteeringJson[key + '_temp'] = value;
}

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

		CTRL_STAT.websocket.send(JSON.stringify(dataToSend));
		CTRL_STAT.isWebSocketOpen = true;

		Object.keys(CTRL_STAT.throttleSteeringJson).forEach((key) => {
			if (key.endsWith('_temp')) {
				delete CTRL_STAT.throttleSteeringJson[key];
			}
		});
	} else {
		if (CTRL_STAT.isWebSocketOpen) {
			console.error('WebSocket is not open. Unable to send data.');
			CTRL_STAT.isWebSocketOpen = false;
		}
	}

	setTimeout(sendJSONCommand, 100);
}

export { addKeyToSentCommand, deltaCoordinatesFromTip, handleDotMove, initializeWS, sendJSONCommand };

