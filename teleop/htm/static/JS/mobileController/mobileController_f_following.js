import CTRL_STAT from './mobileController_z_state.js';

class FollowingHandler {
	constructor(buttonId) {
		this.toggleButton = $(buttonId);
		this.errorLogged = false; // Add this line to initialize the error flag
		this.initialSetup();
		this.startPolling();
	}

	initializeDOM() {
		// $("#mobile_controller_container .current_mode_state").text('Loading...')
		$('#mobile_controller_container .current_mode_button').show();
		$('#mobile_controller_container .current_mode_button').text('start following');
		$('#mobile_controller_container .middle_section').hide();
		$('#mobile_controller_container .square').hide();

		this.sendSwitchFollowingRequest('show_image');

		this.bindButtonAction();
		// It should send the stopping command `sendSwitchFollowingRequest("stop_following")` when I switch the pages
		this.initializeCanvas();
	}
	bindButtonAction() {
		$('#mobile_controller_container .current_mode_button').click(() => {
			if (CTRL_STAT.followingState === 'inactive') {
				this.sendSwitchFollowingRequest('show_image');
			} else if (CTRL_STAT.followingState === 'image') {
				this.sendSwitchFollowingRequest('start_following');
			} else if (CTRL_STAT.followingState === 'active') {
				this.sendSwitchFollowingRequest('show_image');
			}
		});
	}

	initializeCanvas() {
		this.canvas = document.getElementById('following_imageCanvas');
		if (this.canvas) {
			this.ctx = this.canvas.getContext('2d');
		} else {
			setTimeout(() => this.initializeCanvas(), 500); // Retry after 500ms using arrow function
		}
	}

	initialSetup() {
		window.addEventListener('resize', () => this.resizeCanvas());
	}

	sendSwitchFollowingRequest(command) {
		console.log('called with this', command);
		fetch('/fol_handler', {
			method: 'POST',
			headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
			body: `command=${encodeURIComponent(command)}`,
		})
			.then((response) => response.json())
			.catch((error) => console.error('Error sending command:', error));
	}

	startPolling() {
		setInterval(() => {
			if (CTRL_STAT.currentPage == 'follow_link') {
				fetch('/fol_handler', {
					method: 'GET',
					headers: { 'Content-Type': 'application/json' },
				})
					.then((response) => response.json())
					.then((data) => {
						const previousState = CTRL_STAT.followingState;
						this.assignFollowingState(data.following_status);
						this.toggleButtonAppearance();
						if (previousState !== CTRL_STAT.followingState) {
						}
						this.errorLogged = false;
					})
					.catch((error) => {
						if (!this.errorLogged) {
							console.error('Error polling backend:', error);
							this.errorLogged = true;
						}
					});
			}
		}, 500);
	}

	assignFollowingState(backendCommand) {
		// console.log(backendCommand, CTRL_STAT.followingState);
		switch (backendCommand) {
			case 'active':
				CTRL_STAT.followingState = 'active'; // The system is actively following
				break;
			case 'image':
				CTRL_STAT.followingState = 'image'; // The system is doing inference on the current stream from the camera, but not sending movement commands
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
		if (CTRL_STAT.currentPage == 'follow_link') {
			if (CTRL_STAT.followingState == 'image') {
				this.resizeCanvas();
				this.showCanvas();
				$('#mobile_controller_container .current_mode_state').hide();
				$('#mobile_controller_container .square').hide();
				$('#mobile_controller_container .current_mode_button').text('start following');
				$('#mobile_controller_container .current_mode_button').css('background-color', '#ffffff');
				$('#mobile_controller_container .current_mode_button').css('border', '');
			} else if (CTRL_STAT.followingState == 'active') {
				this.resizeCanvas();
				this.showCanvas();
				$('#mobile_controller_container .current_mode_state').hide();
				$('#mobile_controller_container .square').hide();
				$('#mobile_controller_container .current_mode_button').text('stop');
				$('#mobile_controller_container .current_mode_button').css('background-color', '#f41e52');
				$('#mobile_controller_container .current_mode_button').css('border', 'none');
			} else if (CTRL_STAT.followingState == 'inactive') {
				$('#mobile_controller_container .square').show();
				$('#mobile_controller_container .current_mode_state').hide();
				$('#mobile_controller_container .current_mode_button').text('start following');
				$('#mobile_controller_container .current_mode_button').css('background-color', '#ffffff');
				$('#mobile_controller_container .current_mode_button').css('border', '');

				this.hideCanvas();
				// this.toggleButton.innerText = 'Start Following';
				// this.toggleButton.style.backgroundColor = '#67b96a';
			} else if (CTRL_STAT.followingState == 'loading') {
				this.hideCanvas();
				$('#mobile_controller_container .current_mode_state').text('Loading...');
				// this.toggleButton.style.backgroundColor = '#ffa500';
			}
		}
	}

	showCanvas() {
		if (this.canvas) {
			this.canvas.style.display = 'block';
			if (!this.streamActive && !this.intervalId) {
				this.streamActive = true;
				this.intervalId = setInterval(() => this.refreshImage(), 30); // Start streaming
			}
		}
	}

	hideCanvas() {
		if (this.canvas) {
			this.canvas.style.display = 'none';
			if (this.streamActive && this.intervalId) {
				clearInterval(this.intervalId); // Stop streaming
				this.intervalId = null;
				this.streamActive = false;
			}
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
		if (this.canvas) {
			let maxWidth = window.innerWidth * 0.8; // 80% of the viewport width
			if (maxWidth > 640) maxWidth = 640; // Ensuring the width does not exceed 640 pixels
			const maxHeight = (maxWidth * 3) / 4; // Maintain 4:3 ratio

			this.canvas.width = maxWidth;
			this.canvas.height = maxHeight;
			this.canvas.style.width = `${maxWidth}px`;
			this.canvas.style.height = `${maxHeight}px`;
		}
	}
}

var followingNavButtonHandler = new FollowingHandler('.hamburger_menu_nav a#follow_link');

export { followingNavButtonHandler };
