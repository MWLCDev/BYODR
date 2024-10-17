import { page_utils, socket_utils } from '../index_a_utils.js';
import { roverUI, cameraControls } from '../index_c_screen.js';

class MJPEGFrameController {
	constructor() {
		this.targetTimeout = null;
		this.timeSmoothing = 0.8;
		this.actualFps = 0;
		this.targetFps = 0;
		this.duration = 1000;
		this.requestStart = performance.now();
		this.maxJpegQuality = 50;
		this.jpegQuality = 20;
		this.minJpegQuality = 25;
		this.updateFramerate();
	}

	/**
	 * Sets the target frames per second.
	 * @param {number} fps - The target frames per second.
	 */
	setTargetFps(fps) {
		this.actualFps = fps;
		this.targetFps = fps;
		this.targetTimeout = this.targetFps > 0 ? 1000 / this.targetFps : null;
	}

	/**
	 * Gets the actual frames per second.
	 * @returns {number} The actual frames per second.
	 */
	getActualFps() {
		return this.actualFps;
	}

	/**
	 * Updates the frame rate and adjusts JPEG quality based on actual fps.
	 * @returns {number|null} The timeout until the next frame capture.
	 */
	updateFramerate() {
		try {
			if (this.targetTimeout === undefined) {
				this.timeout = null;
			} else {
				const now = performance.now();
				const frameDuration = now - this.requestStart;
				this.duration = this.timeSmoothing * this.duration + (1 - this.timeSmoothing) * frameDuration;
				this.requestStart = now;
				this.actualFps = Math.round(1000.0 / this.duration);
				const qualityStep = Math.min(1, Math.max(-1, this.actualFps - this.targetFps));
				this.jpegQuality = Math.min(this.maxJpegQuality, Math.max(this.minJpegQuality, this.jpegQuality + qualityStep));
				this.timeout = Math.max(0, this.targetTimeout - this.duration);
			}
			return this.timeout;
		} catch (error) {
			console.error('Error updating framerate:', error);
		}
	}
}

class MJPEGControlLocalStorage {
	constructor() {
		/** @type {number} Minimum JPEG quality. */
		this.minJpegQuality = 25;
		/** @type {number} Maximum JPEG quality. */
		this.maxJpegQuality = 50;
		this.load();
	}

	/**
	 * Sets the maximum JPEG quality and adjusts the minimum quality accordingly.
	 * @param {number} val - The maximum quality value.
	 */
	setMaxQuality(val) {
		try {
			if (val > 0 && val <= 100) {
				this.maxJpegQuality = val;
				// Modify the minimum quality in lockstep with the maximum.
				let minQuality = val / 2.0;
				if (minQuality < 5) {
					minQuality = 5;
				}
				this.minJpegQuality = minQuality;
			}
		} catch (error) {
			console.error('Error setting maximum quality:', error);
		}
	}

	/**
	 * Increases the maximum JPEG quality.
	 */
	increaseQuality() {
		this.setMaxQuality(this.maxJpegQuality + 5);
	}

	/**
	 * Decreases the maximum JPEG quality.
	 */
	decreaseQuality() {
		this.setMaxQuality(this.maxJpegQuality - 5);
	}

	/**
	 * Loads the JPEG quality settings from localStorage.
	 */
	load() {
		try {
			const qualityMax = window.localStorage.getItem('mjpeg.quality.max');
			if (qualityMax != null) {
				this.setMaxQuality(JSON.parse(qualityMax));
			}
		} catch (error) {
			console.error('Error loading:', error);
		}
	}

	/**
	 * Saves the JPEG quality settings to localStorage.
	 */
	save() {
		window.localStorage.setItem('mjpeg.quality.max', JSON.stringify(this.maxJpegQuality));
	}
}

class RealCameraController {
	/**
	 * Constructs a RealCameraController.
	 * @param {string} cameraPosition - The position of the camera ('front' or 'rear').
	 * @param {MJPEGFrameController} frameController - The frame controller instance.
	 * @param {function} messageCallback - The callback function to handle messages.
	 */
	constructor(cameraPosition, frameController, messageCallback) {
		this.cameraPosition = cameraPosition;
		this.messageCallback = messageCallback;
		this.frameController = frameController;
		this.socketCaptureTimer = null;
		this.socketCloseTimer = null;
		this.socket = null;
	}

	clearSocketCloseTimer() {
		if (this.socketCloseTimer !== undefined) {
			clearTimeout(this.socketCloseTimer);
		}
	}

	clearSocketCaptureTimer() {
		if (this.socketCaptureTimer !== undefined) {
			clearTimeout(this.socketCaptureTimer);
		}
	}

	/**
	 * Captures a frame from the camera.
	 */
	capture() {
		try {
			this.clearSocketCloseTimer();
			this.clearSocketCaptureTimer();
			this.socketCloseTimer = setTimeout(() => {
				if (this.socket != null) {
					this.socket.close(4001, 'Done waiting for the server to respond.');
				}
			}, 1000);

			if (this.socket != null && this.socket.readyState === 1) {
				this.socket.send(
					JSON.stringify({
						quality: this.frameController.jpegQuality,
					})
				);
			}
		} catch (error) {
			console.error('Error capturing the frame:', error);
		}
	}

	/**
	 * Sets the frame capture rate.
	 * @param {string} rate - The desired rate ('fast', 'slow', 'off').
	 */
	setRate(rate) {
		try {
			switch (rate) {
				case 'fast':
					this.frameController.setTargetFps(16);
					this.socketCaptureTimer = setTimeout(() => {
						this.capture();
					}, 0);
					break;
				case 'slow':
					this.frameController.setTargetFps(4);
					this.socketCaptureTimer = setTimeout(() => {
						this.capture();
					}, 0);
					break;
				default:
					this.frameController.setTargetFps(0);
			}
		} catch (error) {
			console.error('Error setting the frame rate:', error);
		}
	}

	/**
	 * Starts the WebSocket connection to the camera.
	 */
	startSocket() {
		try {
			const cameraUri = `/ws/cam/${this.cameraPosition}`;
			socket_utils.create_socket(cameraUri, true, 250, (ws) => {
				this.socket = ws;
				ws.attempt_reconnect = true;
				ws.is_reconnect = function () {
					return ws.attempt_reconnect;
				};
				ws.onopen = () => {
					// Connection established
				};
				ws.onclose = () => {
					// Connection closed
				};
				ws.onmessage = (evt) => {
					this.clearSocketCloseTimer();
					const timeout = this.frameController.updateFramerate();
					if (timeout !== undefined && timeout >= 0) {
						this.socketCaptureTimer = setTimeout(() => {
							this.capture();
						}, timeout);
					}
					setTimeout(() => {
						let cmd = null;
						if (typeof evt.data === 'string') {
							cmd = evt.data;
						} else {
							cmd = new Blob([new Uint8Array(evt.data)], { type: 'image/jpeg' });
						}
						this.messageCallback(cmd);
					}, 0);
				};
			});
		} catch (error) {
			console.error(`Error while opening ${this.cameraPosition} socket:`, error);
		}
	}

	/**
	 * Stops the WebSocket connection to the camera.
	 */
	stopSocket() {
		try {
			// Clear any pending timers to prevent further execution of capture
			this.clearSocketCloseTimer();
			this.clearSocketCaptureTimer();

			if (this.socket != null) {
				// Checks for both undefined and null
				this.socket.attempt_reconnect = false;
				if (this.socket.readyState < 2) {
					try {
						this.socket.close();
					} catch (err) {
						// Ignore error
					}
				}
				this.socket = null;
			}
		} catch (error) {
			console.error('Error trying to stop the socket:', error);
		}
	}
}

class MJPEGPageController {
	constructor() {
		/** @type {MJPEGControlLocalStorage} Stores JPEG quality settings. */
		this.store = new MJPEGControlLocalStorage();
		/** @type {Array<function>} Listeners for camera initialization. */
		this.cameraInitListeners = [];
		/** @type {Array<function>} Listeners for receiving camera images. */
		this.cameraImageListeners = [];
		/** @type {JQuery<HTMLElement>} jQuery element for the preview image. */
		this.elPreviewImage = null;
		/** @type {JQuery<HTMLElement>} jQuery element for the expand camera icon. */
		this.expandCameraIcon = null;
	}

	/**
	 * Initializes the MJPEG page controller with the provided cameras.
	 * @param {Array<RealCameraController>} cameras - The list of camera controllers.
	 */
	init(cameras) {
		try {
			this.cameras = cameras;
			this.applyLimits();
			this.refreshPageValues();
			this.elPreviewImage = $('img#second_stream_view');
			this.expandCameraIcon = $('img#expand_camera_icon');
			this.expandCameraIcon.css({ cursor: 'zoom-in' });
			this.setCameraFramerates(cameraControls.activeCamera);
			this.bindDomActions();
			// Set the image receiver handlers.
			this.addCameraListener(
				(position, cmd) => {},
				(position, blob) => {
					// Show the other camera in preview.
					if (position !== cameraControls.activeCamera) {
						this.elPreviewImage.attr('src', blob);
					}
				}
			);
		} catch (error) {
			console.error('Error while initializing camera:', error);
		}
	}

	/**
	 * Binds DOM actions for UI interactions.
	 */
	bindDomActions() {
		try {
			$('#caret_down').click(() => {
				this.decreaseQuality();
				this.refreshPageValues();
			});
			$('#caret_up').click(() => {
				this.increaseQuality();
				this.refreshPageValues();
			});
			this.elPreviewImage.click(() => {
				cameraControls.toggleCamera();
			});
			this.expandCameraIcon.click(() => {
				const state = this.elPreviewImage.width() < 480 ? 'small' : 'medium';
				switch (state) {
					case 'small':
						this.elPreviewImage.width(480);
						this.elPreviewImage.height(320);
						this.elPreviewImage.css({ opacity: 0.5 });
						this.expandCameraIcon.css({ cursor: 'zoom-out' });
						break;
					default:
						this.elPreviewImage.width(320);
						this.elPreviewImage.height(240);
						this.elPreviewImage.css({ opacity: 1 });
						this.expandCameraIcon.css({ cursor: 'zoom-in' });
				}
				// Reset the framerate.
				this.setCameraFramerates(cameraControls.activeCamera);
			});
		} catch (error) {
			console.error('Error while binding DOM actions:', error);
		}
	}

	/**
	 * Refreshes the page values related to MJPEG settings.
	 */
	refreshPageValues() {
		$('span#mjpeg_quality_val').text(this.getMaxQuality());
	}

	/**
	 * Adds listeners for camera initialization and image reception.
	 * @param {function} cbInit - Callback for camera initialization.
	 * @param {function} cbImage - Callback for receiving images.
	 */
	addCameraListener(cbInit, cbImage) {
		this.cameraInitListeners.push(cbInit);
		this.cameraImageListeners.push(cbImage);
	}

	/**
	 * Notifies all camera initialization listeners.
	 * @param {string} cameraPosition - The position of the camera.
	 * @param {object} cmd - The initialization command.
	 */
	notifyCameraInitListeners(cameraPosition, cmd) {
		this.cameraInitListeners.forEach((cb) => {
			cb(cameraPosition, cmd);
		});
	}

	/**
	 * Notifies all camera image listeners.
	 * @param {string} cameraPosition - The position of the camera.
	 * @param {string} blob - The image blob URL.
	 */
	notifyCameraImageListeners(cameraPosition, blob) {
		this.cameraImageListeners.forEach((cb) => {
			cb(cameraPosition, blob);
		});
	}

	/**
	 * Applies the JPEG quality limits to all cameras.
	 */
	applyLimits() {
		this.cameras.forEach((cam) => {
			cam.frameController.maxJpegQuality = this.getMaxQuality();
			cam.frameController.minJpegQuality = this.getMinQuality();
		});
	}

	/**
	 * Gets the maximum JPEG quality.
	 * @returns {number} The maximum JPEG quality.
	 */
	getMaxQuality() {
		return this.store.maxJpegQuality;
	}

	/**
	 * Gets the minimum JPEG quality.
	 * @returns {number} The minimum JPEG quality.
	 */
	getMinQuality() {
		return this.store.minJpegQuality;
	}

	/**
	 * Increases the maximum JPEG quality.
	 */
	increaseQuality() {
		this.store.increaseQuality();
		this.applyLimits();
		this.store.save();
	}

	/**
	 * Decreases the maximum JPEG quality.
	 */
	decreaseQuality() {
		this.store.decreaseQuality();
		this.applyLimits();
		this.store.save();
	}

	/**
	 * Sets the frame rates for the cameras based on the active camera.
	 * @param {string} position - The position of the active camera.
	 */
	setCameraFramerates(position) {
		try {
			const isMJPEG = page_utils.get_stream_type() === 'mjpeg';
			const frontCamera = this.cameras.find((cam) => cam.cameraPosition === 'front');
			const rearCamera = this.cameras.find((cam) => cam.cameraPosition === 'rear');
			if (isMJPEG) {
				frontCamera.setRate(position === 'front' ? 'fast' : 'slow');
				rearCamera.setRate(position === 'rear' ? 'fast' : 'slow');
			} else {
				frontCamera.setRate(position === 'front' ? 'off' : 'slow');
				rearCamera.setRate(position === 'rear' ? 'off' : 'slow');
			}
		} catch (error) {
			console.error('Error setting camera frame rates:', error);
		}
	}
}

class MJPEGApplication {
	constructor() {
		this.mjpegPageController = new MJPEGPageController();
		this.frontCameraFrameController = new MJPEGFrameController();
		this.rearCameraFrameController = new MJPEGFrameController();
		this.mjpegRearCamera = null;
		this.mjpegFrontCamera = null;
	}

	init() {
		this.mjpegRearCamera = new RealCameraController('rear', this.rearCameraFrameController, this.createCameraConsumer('rear'));
		this.mjpegFrontCamera = new RealCameraController('front', this.frontCameraFrameController, this.createCameraConsumer('front'));
		this.findCanvasAndExecute();
	}

	/**
	 * Creates a camera consumer function for handling camera data.
	 * @param {string} cameraPosition - The position of the camera.
	 * @returns {function} The camera consumer function.
	 */
	createCameraConsumer(cameraPosition) {
		return (data) => {
			try {
				if (typeof data === 'string') {
					const cmd = JSON.parse(data);
					this.mjpegPageController.notifyCameraInitListeners(cameraPosition, cmd);
				} else {
					const blobUrl = URL.createObjectURL(data);
					this.mjpegPageController.notifyCameraImageListeners(cameraPosition, blobUrl);
					if (cameraPosition === 'rear') {
						$('span#rear_camera_framerate').text(this.rearCameraFrameController.getActualFps().toFixed(0));
					} else if (cameraPosition === 'front') {
						$('span#front_camera_framerate').text(this.frontCameraFrameController.getActualFps().toFixed(0));
					}
				}
			} catch (error) {
				console.error(`Error processing data for ${cameraPosition} camera:`, error);
			}
		};
	}

	/**
	 * Finds the canvas element and initializes the application.
	 */
	findCanvasAndExecute() {
		const canvas = document.getElementById('main_stream_view');
		if (canvas) {
			this.initializeApplication(canvas);
		} else {
			setTimeout(() => this.findCanvasAndExecute(), 500);
		}
	}

	/**
	 * Initializes the application with the provided canvas.
	 * @param {HTMLCanvasElement} canvas - The canvas element.
	 */
	initializeApplication(canvas) {
		try {
			this.mjpegPageController.init([this.mjpegFrontCamera, this.mjpegRearCamera]);
			this.setupStreamTypeSelector();
			this.setupCameraActivationListener();
			this.setupMJPEGCanvasRendering(canvas);
		} catch (error) {
			console.error('Error initializing MJPEG application:', error);
		}
	}

	/**
	 * Sets up the stream type selector dropdown.
	 */
	setupStreamTypeSelector() {
		$('#video_stream_type').change(function () {
			const selectedStreamType = $(this).val();
			page_utils.set_stream_type(selectedStreamType);
			location.reload();
		});
	}

	/**
	 * Sets up the listener for camera activation changes.
	 */
	setupCameraActivationListener() {
		// Set the socket desired fps when the active camera changes.
		cameraControls.addCameraActivationListener((position) => {
			setTimeout(() => {
				this.mjpegPageController.setCameraFramerates(position);
			}, 100);
		});
	}

	/**
	 * Sets up the MJPEG canvas rendering logic.
	 * @param {HTMLCanvasElement} canvas - The canvas element.
	 */
	setupMJPEGCanvasRendering(canvas) {
		if (page_utils.get_stream_type() !== 'mjpeg') return;

		// Create a rendering context for the canvas
		const displayCtx = canvas.getContext('2d');

		// Define the callback function to handle camera initialization
		const handleCameraInit = (position, cmd) => {
			try {
				if (cameraControls.activeCamera === position && cmd.action === 'init') {
					canvas.width = cmd.width;
					canvas.height = cmd.height;
					roverUI.onCanvasInit(cmd.width, cmd.height);
				}
			} catch (error) {
				console.error('Error handling camera initialization:', error);
			}
		};

		// Define the callback function to handle image rendering
		const handleImageRendering = (position, blobUrl) => {
			try {
				if (cameraControls.activeCamera === position) {
					const img = new Image();
					img.onload = function () {
						try {
							requestAnimationFrame(() => {
								// Ensure the canvas draws are not run in parallel
								displayCtx.drawImage(img, 0, 0);
								roverUI.canvasUpdate(displayCtx);
							});
						} catch (error) {
							console.error('Error during image rendering:', error);
						}
					};
					// Set the src to trigger the image load
					img.src = blobUrl;
				}
			} catch (error) {
				console.error('Error handling image rendering:', error);
			}
		};

		// Add the camera listeners with the new functions
		try {
			this.mjpegPageController.addCameraListener(handleCameraInit, handleImageRendering);
		} catch (error) {
			console.error('Error setting up camera listeners:', error);
		}
	}

	/**
	 * Starts all MJPEG streams.
	 */
	startAll() {
		this.findCanvasAndRebind();
		if (this.mjpegRearCamera) {
			this.mjpegRearCamera.startSocket();
		}
		if (this.mjpegFrontCamera) {
			this.mjpegFrontCamera.startSocket();
		}
	}

	/**
	 * Stops all MJPEG streams.
	 */
	stopAll() {
		if (this.mjpegRearCamera) {
			this.mjpegRearCamera.stopSocket();
		}
		if (this.mjpegFrontCamera) {
			this.mjpegFrontCamera.stopSocket();
		}
	}

	/**
	 * Finds and rebinds the canvas and image elements.
	 */
	findCanvasAndRebind() {
		// Find the canvas and img DOM elements
		const canvas = document.getElementById('main_stream_view');
		const imgPreview = document.querySelector('img#second_stream_view');

		// Check if elements are found, and rebind them to their respective listeners
		if (canvas && imgPreview) {
			this.mjpegPageController.elPreviewImage = $(imgPreview);
			this.setupMJPEGCanvasRendering(canvas); // Re-bind the canvas rendering logic
		} else {
			setTimeout(() => this.findCanvasAndRebind(), 500); // Retry if elements are not ready yet
		}
	}
}

// Create a singleton instance of MJPEGApplication
const mjpegApp = new MJPEGApplication();

export function mjpegInit() {
	mjpegApp.init();
}

export function mjpegStartAll() {
	mjpegApp.startAll();
}

export function mjpegStopAll() {
	mjpegApp.stopAll();
}
