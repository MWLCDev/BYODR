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

// Function to add any additional data
function addDataToMobileCommand(dataPairs) {
	for (let key in dataPairs) {
		if (dataPairs.hasOwnProperty(key) && dataPairs[key] !== '' && dataPairs[key] !== null && dataPairs[key] !== undefined) {
			let value = isNaN(dataPairs[key]) ? dataPairs[key] : Number(dataPairs[key]);
			CTRL_STAT.mobileCommandJSON[key] = value;
		}
	}
}

export { setMobileCommand, addDataToMobileCommand };
