import { ControlSquare } from './mobileController_b_shape_square.js';

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
