import CTRL_STAT from '../mobileController_z_state.js';

class FollowingHandler {
	constructor() {
		this.errorLogged = false;
		this.initialSetup();
		this.startPolling();
	}

	initializeDOM() {
		$('body').addClass('following-feature');
		this.sendSwitchFollowingRequest('show_image');
		this.bindButtonAction();
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
			setTimeout(() => this.initializeCanvas(), 500);
		}
	}

	initialSetup() {
		window.addEventListener('resize', () => this.resizeCanvas());
	}

	sendSwitchFollowingRequest(command) {
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
							// Additional actions can be added here if needed when state changes
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
		switch (backendCommand) {
			case 'active':
				CTRL_STAT.followingState = 'active';
				break;
			case 'image':
				CTRL_STAT.followingState = 'image';
				break;
			case 'inactive':
				CTRL_STAT.followingState = 'inactive';
				break;
			case 'loading':
				CTRL_STAT.followingState = 'loading';
				break;
			default:
				console.log('Following: Unknown command received from the backend:', backendCommand);
		}
	}

	toggleButtonAppearance() {
		$('body').removeClass('image-mode active-mode inactive-mode loading-mode');

		if (CTRL_STAT.followingState === 'image') {
			this.resizeCanvas();
			this.showCanvas();
			$('body').addClass('image-mode');
		} else if (CTRL_STAT.followingState === 'active') {
			this.resizeCanvas();
			this.showCanvas();
			$('body').addClass('active-mode');
		} else if (CTRL_STAT.followingState === 'inactive') {
			$('body').addClass('inactive-mode');
			this.hideCanvas();
		} else if (CTRL_STAT.followingState === 'loading') {
			$('body').addClass('loading-mode');
			this.hideCanvas();
		}
	}

	showCanvas() {
		if (this.canvas) {
			this.canvas.style.display = 'block';
			if (!this.streamActive && !this.intervalId) {
				this.streamActive = true;
				this.intervalId = setInterval(() => this.refreshImage(), 30);
			}
		}
	}

	hideCanvas() {
		if (this.canvas) {
			this.canvas.style.display = 'none';
			if (this.streamActive && this.intervalId) {
				clearInterval(this.intervalId);
				this.intervalId = null;
				this.streamActive = false;
			}
		}
	}

	refreshImage() {
		if (!this.streamActive) return;

		const img = new Image();
		img.onload = () => {
			this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
			this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
		};
		img.src = '/latest_image?' + new Date().getTime();
	}

	resizeCanvas() {
		if (this.canvas) {
			let maxWidth = window.innerWidth * 0.8;
			if (maxWidth > 640) maxWidth = 640;
			const maxHeight = (maxWidth * 3) / 4;

			this.canvas.width = maxWidth;
			this.canvas.height = maxHeight;
			this.canvas.style.width = `${maxWidth}px`;
			this.canvas.style.height = `${maxHeight}px`;
		}
	}
}

var followingNavButtonHandler = new FollowingHandler();
export { followingNavButtonHandler };
