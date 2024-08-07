import CTRL_STAT from './mobileController_z_state.js';
// Function to set throttle and steering

function setMobileCommand(x, y) {
	// Always set throttle and steering explicitly
	CTRL_STAT.mobileCommandJSON.throttle = Number(y);
	CTRL_STAT.mobileCommandJSON.steering = Number(x);
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
