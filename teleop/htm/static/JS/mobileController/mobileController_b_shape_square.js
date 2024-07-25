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
		this.lastX = 0;
		this.lastY = 0;
		this.lastTime = Date.now();
		this.frames = [];

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
		const currentTime = Date.now();
		const timeDifference = currentTime - this.lastTime;
		const dist = Math.sqrt((x - this.lastX) ** 2 + (y - this.lastY) ** 2);
		const speed = dist / timeDifference;

		const frame = {
			startX: this.lastX,
			startY: this.lastY,
			endX: x,
			endY: y,
			speed: speed,
		};

		this.frames.push(frame);
		if (this.frames.length > 10) this.frames.shift();
		this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);

		this.frames.forEach((frame, index) => {
			this.context.beginPath();
			this.context.moveTo(frame.startX, frame.startY);
			this.context.lineTo(frame.endX, frame.endY);
			const factor = (index + 1) / this.frames.length;
			const lineWidth = factor * 8 + 2;
			this.context.strokeStyle = '#451c58';
			this.context.lineWidth = lineWidth;
			this.context.stroke();
		});

		this.context.shadowBlur = 10;
		this.context.shadowColor = 'rgba(0, 0, 0, 0.5)';
		this.context.shadowOffsetX = 0;
		this.context.shadowOffsetY = 5;
		this.context.fillStyle = '#694978';
		this.context.beginPath();
		this.context.arc(x, y, 10, 0, Math.PI * 2);
		this.context.fill();
		this.context.shadowBlur = 0;
		this.context.shadowColor = 'transparent';

		this.lastX = x;
		this.lastY = y;
		this.lastTime = currentTime;
	}

	handleMouseEvent(e) {
		e.preventDefault();
		if (e.type === 'mousedown') {
			this.isDrawing = true;
			this.otherSquare.style.borderColor = 'red';
			this.otherStopText.style.display = 'block';
			this.otherDirectionText.style.display = 'none';
		} else if (!this.isDrawing) {
			return;
		}
		const x = e.clientX;
		const y = e.clientY;
		this.updateCoordinates(x, y, this.canvas.getBoundingClientRect());
	}

	handleTouchEvent(e) {
		e.preventDefault();
		if (e.type === 'touchstart') {
			this.isDrawing = true;
			this.otherSquare.style.borderColor = 'red';
			this.otherStopText.style.display = 'block';
			this.otherDirectionText.style.display = 'none';
		} else if (!this.isDrawing) {
			return;
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
