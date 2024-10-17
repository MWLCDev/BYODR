class ControlSettings {
	constructor() {
		this.cacheDomElements();
		this.initializeSettings();
	}

	cacheDomElements() {
		// Caching DOM elements
		this.scaleInput = $('#scale_input');
		this.offsetInput = $('#offset_input');
		this.deadZoneInput = $('#dead_zone_input');

		this.scaleInputText = $('#scale_input_value');
		this.offsetInputText = $('#offset_input_value');
		this.deadZoneInputText = $('#dead_zone_width_value');

		this.channel3Toggle = $('#channel3-toggle');
		this.channel4Toggle = $('#channel4-toggle');
	}

	initializeSettings() {
		this.fetchAndUpdateRoverData();
		this.setupInputListeners();
		this.setupRelayToggleListeners();
		this.fetchAndUpdateRelayStates();
	}

	setupInputListeners() {
		this.bindSliderChangeEvents();
		this.bindSliderValueUpdates();
	}

	bindSliderChangeEvents() {
		// Sends data to the backend when the slider values change
		this.scaleInput
			.add(this.offsetInput)
			.add(this.deadZoneInput)
			.on('change touchend', () => this.sendSliderDataToBackend());
	}

	bindSliderValueUpdates() {
		// Updates the text values based on slider inputs
		this.scaleInput.on('input touchmove', () => this.updateSliderValue(this.scaleInput, this.scaleInputText));
		this.offsetInput.on('input touchmove', () => this.updateSliderValue(this.offsetInput, this.offsetInputText));
		this.deadZoneInput.on('input touchmove', () => this.updateSliderValue(this.deadZoneInput, this.deadZoneInputText));
	}

	updateSliderValue(input, displayElement) {
		displayElement.text(input.val());
	}

	fetchAndUpdateRoverData() {
		// Fetches rover data and updates input fields accordingly
		$.get('/teleop/user/options')
			.done((data) => this.updateInputsFromData(data))
			.fail((error) => console.error('Error fetching rover data:', error));
	}

	updateInputsFromData(data) {
		this.scaleInput.val(data.vehicle['ras.driver.motor.scale']).trigger('input');
		this.offsetInput.val(data.vehicle['ras.driver.steering.offset']).trigger('input');
		this.deadZoneInput.val(data.vehicle['ras.driver.deadzone.width']).trigger('input');
	}

	sendSliderDataToBackend() {
		const data = {
			vehicle: this.getSliderData(),
		};

		$.ajax({
			url: '/teleop/user/options',
			method: 'POST',
			contentType: 'application/json',
			data: JSON.stringify(data),
			error: (error) => console.error('Error sending data to backend:', error),
		});
	}

	getSliderData() {
		// Collects slider data to be sent to the backend
		return [
			['ras.driver.motor.scale', this.scaleInput.val()],
			['ras.driver.steering.offset', this.offsetInput.val()],
			['ras.driver.deadzone.width', this.deadZoneInput.val()],
		].filter(([key, value]) => value !== '');
	}

	fetchAndUpdateRelayStates() {
		// Fetches relay states and updates the UI
		const relayUrl = `${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`;
		$.get(relayUrl)
			.done((response) => this.updateRelayControls(response.states))
			.fail((error) => console.error('Error updating relay states:', error));
	}

	updateRelayControls(states) {
		$('.channel').each(function () {
			const index = $(this).data('index');
			const state = states[index] === true;
			$(this).find(`input[value="${state}"]`).prop('checked', state);
		});
	}

	setupRelayToggleListeners() {
		// Sets up listeners for relay toggle buttons
		this.bindToggleListener(this.channel3Toggle);
		this.bindToggleListener(this.channel4Toggle);
	}

	bindToggleListener(toggleElement) {
		// These relays aren't used in the smaller boxes and they were not used with the older boxes. There is no need to implement the full logic for them here
		toggleElement.on('change', () => {}).trigger('change');
	}
}

export { ControlSettings };
