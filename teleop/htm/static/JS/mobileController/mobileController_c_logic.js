import CTRL_STAT from './mobileController_z_state.js';

function setMobileCommand(x, y) {
	if (typeof x === 'number' && typeof y === 'number') {
		CTRL_STAT.mobileCommandJSON.throttle = Number(y);
		CTRL_STAT.mobileCommandJSON.steering = Number(x);
		CTRL_STAT.mobileCommandJSON.button_b = '1';
	} else if (typeof x === 'string' && typeof y === 'string') {
		CTRL_STAT.mobileCommandJSON.throttle = y;
		CTRL_STAT.mobileCommandJSON.steering = x;
	} else {
		console.error('Invalid types for setMobileCommand:', { x, y });
	}
}

function addDataToMobileCommand(newData) {
	// Iterate through the keys of the new data
	Object.keys(newData).forEach((key) => {
		// Only add the key if it doesn't already exist in mobileCommandJSON
		if (!CTRL_STAT.mobileCommandJSON.hasOwnProperty(key)) {
			CTRL_STAT.mobileCommandJSON[key] = newData[key];
		}
	});
}

export { setMobileCommand, addDataToMobileCommand };
