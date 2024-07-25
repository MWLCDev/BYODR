import { ControlSquare } from './mobileController_b_shape_square.js';
// import { initializeWS, sendJSONCommand } from './mobileController_c_logic.js';
import CTRL_STAT from './mobileController_z_state.js'; // Stands for control state

const mobileUI = document.getElementById('mobile_controller_container');
const forwardSquare = new ControlSquare(mobileUI.querySelector('#forward_square'), mobileUI.querySelector('#backward_square'));
const backwardSquare = new ControlSquare(mobileUI.querySelector('#backward_square'), mobileUI.querySelector('#forward_square'));

function resizeAllCanvases() {
	forwardSquare.resizeCanvas();
	backwardSquare.resizeCanvas();
}

// Handle resizing
window.addEventListener('resize', resizeAllCanvases);
resizeAllCanvases();
