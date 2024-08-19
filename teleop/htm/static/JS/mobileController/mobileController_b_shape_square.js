import CTRL_STAT from './mobileController_z_state.js';
import { setMobileCommand } from './mobileController_c_logic.js';

class ControlSquare {
	constructor(element, otherSquare) {
		this.square = element;
		this.canvas = element.querySelector('canvas');
		this.context = this.canvas.getContext('2d');
		this.stopText = element.querySelector('.stop_text');
		this.directionText = element.querySelector('.square_text');

		this.otherSquare = otherSquare;
		this.otherCanvas = otherSquare.querySelector('canvas');
		this.otherContext = this.otherCanvas.getContext('2d');
		this.otherStopText = otherSquare.querySelector('.stop_text');
		this.otherDirectionText = otherSquare.querySelector('.square_text');

		this.isDrawing = false;
    this.isTransitioning = false;  // Flag to detect if a transition between squares is occurring
		this.initX = 0;
		this.initY = 0;
		this.lastX = 0;
		this.lastY = 0;
		this.lastTime = Date.now();

		this.initEventListeners();
	}

	resizeCanvas() {
		this.canvas.width = this.canvas.offsetWidth;
		this.canvas.height = this.canvas.offsetHeight;
	}

	updateCoordinates(x, y, clientRect) {
    if (this.isTransitioning) return;  // Stop updating coordinates if transitioning
		x -= clientRect.left;
		y -= clientRect.top;

		// Clamp x and y within canvas boundaries considering the estimated radius of the ball
		const minX = 10,
			maxX = this.canvas.width - 10;
		const minY = 10,
			maxY = this.canvas.height - 10;
		x = Math.max(minX, Math.min(x, maxX));
		y = Math.max(minY, Math.min(y, maxY));

		this.drawPin(x, y);
		// Calculate normalized X
		let normalizedX = (x - this.initX) / (this.canvas.width / 3);
		normalizedX = Math.max(-1, Math.min(normalizedX, 1));

		// Calculate and adjust normalized Y based on whether the control is 'forward' or 'backward'
		// the value should increase if the ball moves upwards on the y-axis for the forward triangle, and vice-verse for the backwards one.
		let deltaY = this.square.id === 'backward_square' ? y - this.initY : this.initY - y;
		let scaleFactor = this.canvas.height / 5;
		let normalizedY = deltaY / scaleFactor;

		// Apply directional flipping for backward square
		if (this.square.id === 'backward_square') {
			normalizedY = -normalizedY;
			normalizedY = Math.max(-1, Math.min(normalizedY, 0));
		} else {
			normalizedY = Math.max(0, Math.min(normalizedY, 1));
		}

		// Optionally call a callback function if set

		setMobileCommand(Number(normalizedX.toFixed(3)), Number(normalizedY.toFixed(3)), 'auto');
	}


	switchCanvasDisplay(command) {
		this.canvas.style.display = command;
	}

	drawPin(x, y) {
		this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);

		// Draw the line from initial point to current point
		this.context.beginPath();
		this.context.moveTo(this.initX, this.initY);
		this.context.lineTo(x, y);
		this.context.strokeStyle = '#451c58';
		this.context.lineWidth = 4;
		this.context.stroke();

		// Draw the pin with the shadow at the current location
		this.context.shadowBlur = 10;
		this.context.shadowColor = 'rgba(0, 0, 0, 0.5)';
		this.context.shadowOffsetX = 0;
		this.context.shadowOffsetY = 5;
		this.context.fillStyle = '#694978';
		this.context.beginPath();
		this.context.arc(x, y, 10, 0, Math.PI * 2);
		this.context.fill();
		this.lastX = x;
		this.lastY = y;
		// Reset shadow for any other drawing
		this.context.shadowBlur = 0;
		this.context.shadowColor = 'transparent';
	}

	fadeOutDrawing() {
		let opacity = 1; // Start with full opacity
		const fade = () => {
			this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
			this.context.globalAlpha = opacity; // Apply current opacity to drawing

			// Redraw the line
			this.context.beginPath();
			this.context.moveTo(this.initX, this.initY);
			this.context.lineTo(this.lastX, this.lastY);
			this.context.strokeStyle = '#451c58';
			this.context.lineWidth = 4;
			this.context.stroke();

			// Redraw the pin
			this.context.shadowBlur = 10;
			this.context.shadowColor = `rgba(0, 0, 0, ${opacity * 0.5})`;
			this.context.shadowOffsetX = 0;
			this.context.shadowOffsetY = 5;
			this.context.fillStyle = '#694978';
			this.context.beginPath();
			this.context.arc(this.lastX, this.lastY, 10, 0, Math.PI * 2);
			this.context.fill();
			this.context.shadowBlur = 0;
			this.context.shadowColor = 'transparent';

			opacity -= 0.01; // Decrease opacity
			if (opacity > 0) {
				requestAnimationFrame(fade); // Continue animation if not fully transparent
			} else {
				this.context.clearRect(0, 0, this.canvas.width, this.canvas.height); // Clear canvas after fade out
				this.context.globalAlpha = 1; // Reset opacity
			}
		};
		fade(); // Start the fade-out animation
	}

	showOtherSquare(cmd) {
		if (cmd) {
			this.otherSquare.style.borderColor = 'red';
			this.otherStopText.style.display = 'block';
			this.otherDirectionText.style.display = 'none';
		} else {
			this.otherSquare.style.borderColor = '#f6f6f6';
			this.otherStopText.style.display = 'none';
			this.otherDirectionText.style.display = 'block';
		}
	}

	handleTouchEvent(e) {
		e.preventDefault();

		switch (e.type) {
			case 'touchstart':
				this.startDrawing(e.touches[0]);
				break;
			case 'touchmove':
				if (!this.isDrawing) return;
				this.handleTouchMove(e.touches[0]);
				break;
			case 'touchend':
			case 'touchcancel':
				this.stopDrawing();
				break;
		}
	}

	startDrawing(touch) {
    this.isTransitioning = false;  
		this.isDrawing = true;
		const rect = this.canvas.getBoundingClientRect();
		this.initX = touch.clientX - rect.left; // Set initial X
		this.initY = touch.clientY - rect.top; // Set initial Y
		this.showOtherSquare(true);
	}

	handleTouchMove(touch) {
		const x = touch.clientX;
		const y = touch.clientY;
		const currentRect = this.canvas.getBoundingClientRect();
		const otherRect = this.otherCanvas.getBoundingClientRect();

		if (this.detectSquareTransition(y, currentRect, otherRect)) {
			this.triggerSquareTransitionAlert();
		}

		this.updateCoordinates(x, y, currentRect);
	}

	detectSquareTransition(y, currentRect, otherRect) {
		if (this.square.id === 'forward_square' && y > currentRect.bottom && y < otherRect.bottom && y > otherRect.top) {
			return true;
		}

		if (this.square.id === 'backward_square' && y < currentRect.top && y > otherRect.top && y < otherRect.bottom) {
			return true;
		}

		return false;
	}

	triggerSquareTransitionAlert() {
    this.isTransitioning = true;  
		console.log(`Moved from ${this.square.id === 'forward_square' ? 'forward' : 'backward'} square to ${this.square.id === 'forward_square' ? 'backward' : 'forward'} square!`);
		setMobileCommand('force_stop', 'force_stop');
	}

	stopDrawing() {
		CTRL_STAT.mobileCommandJSON = { steering: 0, throttle: 0 }; // send the stopping signal for the motors
		this.fadeOutDrawing(); // Call the fade-out method instead of immediate clear
		this.showOtherSquare(false);
	}

	initEventListeners() {
		this.canvas.addEventListener('touchstart', (e) => this.handleTouchEvent(e, this));
		this.canvas.addEventListener('touchmove', (e) => this.handleTouchEvent(e, this));
		this.canvas.addEventListener('touchend', () => this.stopDrawing());
		this.canvas.addEventListener('touchcancel', () => this.stopDrawing());
	}
}

export { ControlSquare };
