import { redraw, removeTriangles } from './mobileController_d_pixi.js';
import CTRL_STAT from './mobileController_z_state.js';

class ToggleButtonHandler {
	constructor(buttonId) {
		this.toggleButton = document.getElementById(buttonId);
		this.topInputDiv = document.getElementById('mobile-controller-top-input-container');
		this.inferenceToggleBtn = document.getElementById('inference_toggle_button');
		this.confidenceToggleBtn = document.getElementById('confidenceToggleButton');
		this.canvas = document.getElementById('following_imageCanvas');
		this.ctx = this.canvas.getContext('2d');
		this.initialSetup();
		this.startPolling();
	}

	initialSetup() {
		this.resizeCanvas();
		window.addEventListener('resize', () => this.resizeCanvas());
		this.toggleButton.addEventListener('click', () => this.handleFollowingToggleButtonClick());
	}

	handleFollowingToggleButtonClick() {
		if (CTRL_STAT.followingState == 'inactive') {
			this.sendSwitchFollowingRequest('start_following');
		} else if (CTRL_STAT.followingState == 'active') {
			this.sendSwitchFollowingRequest('stop_following');
		}
	}

	sendSwitchFollowingRequest(command) {
    console.log(command)
		fetch('/switch_following', {
			method: 'POST',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
			body: `command=${encodeURIComponent(command)}`,
		})
			.then((response) => response.json())
			.catch((error) => console.error('Error sending command:', error));
	}

	startPolling() {
		setInterval(() => {
			fetch('/switch_following_status', {
				method: 'GET',
				headers: { 'Content-Type': 'application/json' },
			})
				.then((response) => response.json())
				.then((data) => {
					const previousState = CTRL_STAT.followingState;
					this.assignFollowingState(data.following_status);
					// Only call this function if the current state changed from the received one
					if (previousState !== CTRL_STAT.followingState) {
						this.toggleButtonAppearance();
					}
				})
				.catch((error) => console.error('Error polling backend:', error));
		}, 500);
	}

	controlInputControllerVisibility(command) {
		this.topInputDiv.style.display = command;
		this.inferenceToggleBtn.style.display = command;
		this.confidenceToggleBtn.style.display = command;
	}

	assignFollowingState(backendCommand) {
		// console.log(backendCommand, this._followingState)
		switch (backendCommand) {
			case 'active':
				CTRL_STAT.followingState = 'active'; // The system is actively following
				break;
			case 'inactive':
				CTRL_STAT.followingState = 'inactive'; // The system is ready and not following
				break;
			case 'loading':
				CTRL_STAT.followingState = 'loading'; // The system is loading
				break;
			default:
				console.log('Following: Unknown command received from the backend:', backendCommand);
		}
	}

	toggleButtonAppearance() {
		if (CTRL_STAT.followingState == 'active') {
			removeTriangles();
			this.showCanvas();
			this.controlInputControllerVisibility('none');
			this.toggleButton.innerText = 'Stop Following';
			this.toggleButton.style.backgroundColor = '#ff6347';
		} else if (CTRL_STAT.followingState == 'inactive') {
			redraw(undefined, true, true, true);
			this.hideCanvas();
			this.controlInputControllerVisibility('flex');
			this.toggleButton.innerText = 'Start Following';
			this.toggleButton.style.backgroundColor = '#67b96a';
		} else if (CTRL_STAT.followingState == 'loading') {
			this.hideCanvas();
			controlInputControllerVisibility('flex');
			this.toggleButton.innerText = 'Loading...';
			this.toggleButton.style.backgroundColor = '#ffa500';
		}
	}

	showCanvas() {
		this.canvas.style.display = 'block';
		if (!this.streamActive && !this.intervalId) {
			this.streamActive = true;
			this.intervalId = setInterval(() => this.refreshImage(), 150); // Start streaming
		}
	}

	hideCanvas() {
		this.canvas.style.display = 'none';
		if (this.streamActive && this.intervalId) {
			clearInterval(this.intervalId); // Stop streaming
			this.intervalId = null;
			this.streamActive = false;
		}
	}

	refreshImage() {
		if (!this.streamActive) return; // Do not proceed if streaming is not active

		const img = new Image();
		img.onload = () => {
			this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height); // Clear previous image
			this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height); // Draw new image
		};
		img.src = '/latest_image?' + new Date().getTime(); // Include cache busting to prevent loading from cache
	}

	resizeCanvas() {
		if (CTRL_STAT.followingState == 'active') {
			removeTriangles();
		}
		let maxWidth = window.innerWidth * 0.8; // 80% of the viewport width
		if (maxWidth > 640) maxWidth = 640; // Ensuring the width does not exceed 640 pixels
		const maxHeight = (maxWidth * 3) / 4; // Maintain 4:3 ratio

		this.canvas.width = maxWidth;
		this.canvas.height = maxHeight;
		this.canvas.style.width = `${maxWidth}px`;
		this.canvas.style.height = `${maxHeight}px`;
	}

	getAttribute(attributeName) {
		return this.toggleButton.getAttribute(attributeName);
	}

	setAttribute(attributeName, value) {
		this.toggleButton.setAttribute(attributeName, value);
	}

	getStyle(property) {
		return this.toggleButton.style[property];
	}

	setStyle(property, value) {
		this.toggleButton.style[property] = value;
	}
}

const followingButtonHandler = new ToggleButtonHandler('following_toggle_button');

export { followingButtonHandler };
