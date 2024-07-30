import { ControlSquare } from './mobileController_b_shape_square.js';
import { setStatistics } from './mobileController_c_logic.js';
import CTRL_STAT from './mobileController_z_state.js'; // Stands for control state

// Declare these variables at the module level so they are accessible in both functions
let forwardSquare;
let backwardSquare;

export function setupMobileController() {
	const mobileUI = document.getElementById('mobile_controller_container');
	if (mobileUI) {
    CTRL_STAT.state = true
		// Check if the mobile UI container exists
		const forwardSquareElem = mobileUI.querySelector('#forward_square');
		const backwardSquareElem = mobileUI.querySelector('#backward_square');

		// Initialize the ControlSquare instances
		forwardSquare = new ControlSquare(forwardSquareElem, backwardSquareElem);
		backwardSquare = new ControlSquare(backwardSquareElem, forwardSquareElem);

		// Set the callback for each ControlSquare instance
		forwardSquare.setValueUpdateCallback(printNormalizedValues);
		backwardSquare.setValueUpdateCallback(printNormalizedValues);

		// Handle resizing
		window.addEventListener('resize', resizeAllCanvases);
		resizeAllCanvases();
	}
}

function resizeAllCanvases() {
	// Check if the squares are initialized before calling methods on them
	if (forwardSquare && backwardSquare) {
		forwardSquare.resizeCanvas();
		backwardSquare.resizeCanvas();
	}
}

function printNormalizedValues(x, y) {
	setStatistics(x, y, 'auto');
	// console.log(`X: ${x}, Y: ${y}`);
}
