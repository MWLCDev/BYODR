class ControlSquare {
	constructor(element, otherSquare) {
		this.square = element;
		this.canvas = element.querySelector('canvas');
		this.context = this.canvas.getContext('2d');
		this.stopText = element.querySelector('.stop_text');
		this.directionText = element.querySelector('.square_direction_text');

		this.otherSquare = otherSquare;
		this.otherCanvas = otherSquare.querySelector('canvas');
		this.otherContext = this.otherCanvas.getContext('2d');
		this.otherStopText = otherSquare.querySelector('.stop_text');
		this.otherDirectionText = otherSquare.querySelector('.square_direction_text');

		this.isDrawing = false;
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
		x -= clientRect.left;
		y -= clientRect.top;
		//10 is a close estimation to the radius of the ball
		x = Math.max(10, Math.min(x, this.canvas.width - 10));
		y = Math.max(10, Math.min(y, this.canvas.height - 10));
		this.drawPin(x, y);
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

		// Reset shadow for any other drawing
		this.context.shadowBlur = 0;
		this.context.shadowColor = 'transparent';
	}

	handleMouseEvent(e) {
		e.preventDefault();
		if (e.type === 'mousedown') {
			this.isDrawing = true;
			this.initX = e.clientX - this.canvas.getBoundingClientRect().left; // Set initial X
			this.initY = e.clientY - this.canvas.getBoundingClientRect().top; // Set initial Y
			this.otherSquare.style.borderColor = 'red';
			this.otherStopText.style.display = 'block';
			this.otherDirectionText.style.display = 'none';
		} else if (e.type === 'mousemove') {
			if (!this.isDrawing) return;
			const rect = this.canvas.getBoundingClientRect();
			if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {
				if (this.square !== this.otherSquare) {
					alert('Moved from one square to the other!');
				}
			}
		}
		const x = e.clientX;
		const y = e.clientY;
		this.updateCoordinates(x, y, this.canvas.getBoundingClientRect());
	}

	handleTouchEvent(e) {
		e.preventDefault();
		if (e.type === 'touchstart') {
			this.isDrawing = true;
			const touch = e.touches[0];
			this.initX = touch.clientX - this.canvas.getBoundingClientRect().left; // Set initial X
			this.initY = touch.clientY - this.canvas.getBoundingClientRect().top; // Set initial Y
			this.otherSquare.style.borderColor = 'red';
			this.otherStopText.style.display = 'block';
			this.otherDirectionText.style.display = 'none';
		} else if (e.type === 'touchmove') {
			if (!this.isDrawing) return;
			const touch = e.touches[0];
			const rect = this.canvas.getBoundingClientRect();
			if (touch.clientX < rect.left || touch.clientX > rect.right || touch.clientY < rect.top || touch.clientY > rect.bottom) {
				if (this.square !== this.otherSquare) {
					alert('Moved from one square to the other!');
				}
			}
		}
		const touch = e.touches[0];
		const x = touch.clientX;
		const y = touch.clientY;
		this.updateCoordinates(x, y, this.canvas.getBoundingClientRect());
	}

	stopDrawing() {
		this.isDrawing = false;
		this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
		this.frames = [];
		this.otherSquare.style.borderColor = '#f6f6f6';
		this.otherStopText.style.display = 'none';
		this.otherDirectionText.style.display = 'block';
	}

	initEventListeners() {
		this.canvas.addEventListener('mousedown', (e) => this.handleMouseEvent(e, this));
		this.canvas.addEventListener('mousemove', (e) => this.handleMouseEvent(e, this));
		this.canvas.addEventListener('mouseup', () => this.stopDrawing());

		this.canvas.addEventListener('touchstart', (e) => this.handleTouchEvent(e, this));
		this.canvas.addEventListener('touchmove', (e) => this.handleTouchEvent(e, this));
		this.canvas.addEventListener('touchend', () => this.stopDrawing());
		this.canvas.addEventListener('touchcancel', () => this.stopDrawing());
	}
}

export { ControlSquare };
