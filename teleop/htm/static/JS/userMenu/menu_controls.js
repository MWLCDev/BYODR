class ControlSettings {
	constructor() {
		this.scaleInput = $('#scale_input');
		this.offsetInput = $('#offset_input');
		this.deadZoneInput = $('#dead_zone_input');

		this.scaleInputText = $('#scale_input_value');
		this.offsetInputText = $('#offset_input_value');
		this.deadZoneInputText = $('#dead_zone_width_value');

		this.channel3Toggle = $('#channel3-toggle');
		this.channel4Toggle = $('#channel4-toggle');

		this.initDomElements();
	}

	initDomElements() {
		this.fetchRoverData();
		this.bindSliderInputListeners();
		this.bindToggleListeners();
		this.updateRelayStates();
	}

	bindSliderInputListeners() {
		this.scaleInput.on('input touchmove', () => {
			this.scaleInputText.text(this.scaleInput.val());
		});
		this.offsetInput.on('input touchmove', () => {
			this.offsetInputText.text(this.offsetInput.val());
		});
		this.deadZoneInput.on('input touchmove', () => {
			this.deadZoneInputText.text(this.deadZoneInput.val());
		});

		this.scaleInput
			.add(this.offsetInput)
			.add(this.deadZoneInput)
			.on('change touchend', () => {
				this.sendDataToBackend();
			});
	}

	bindToggleListeners() {
		this.channel3Toggle.on('click', () => {
			this.channel3Toggle.toggleClass('active');
			this.sendToggleStateToBackend(2, this.channel3Toggle.hasClass('active'));
		});

		this.channel4Toggle.on('click', () => {
			this.channel4Toggle.toggleClass('active');
			this.sendToggleStateToBackend(3, this.channel4Toggle.hasClass('active'));
		});
	}

	sendToggleStateToBackend(channelIndex, isActive) {
		let data = {
			channel: channelIndex,
			state: isActive,
		};

		$.ajax({
			url: '/teleop/pilot/controls/relay/state',
			method: 'POST',
			contentType: 'application/json',
			data: JSON.stringify(data),
			error: (error) => console.error('Error sending toggle state:', error),
		});
	}

	fetchRoverData() {
		$.get('/teleop/user/options')
			.done((data) => {
				this.scaleInput.val(data.vehicle['ras.driver.motor.scale']).trigger('input');
				this.offsetInput.val(data.vehicle['ras.driver.steering.offset']).trigger('input');
				this.deadZoneInput.val(data.vehicle['ras.driver.deadzone.width']).trigger('input');
			})
			.fail((error) => console.error('Error fetching data:', error));
	}

	updateRelayStates() {
		$.get(`${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`)
			.done((response) => {
				const channel3State = response.states[2] === true;
				const channel4State = response.states[3] === true;

				this.channel3Toggle.toggleClass('active', channel3State);
				this.channel4Toggle.toggleClass('active', channel4State);
			})
			.fail((error) => console.error('Error updating relay states:', error));
	}

	bindBoldTextListeners() {
		const bindAndUpdate = (toggle) => {
			toggle.on('change', () => {}).trigger('change');
		};

		bindAndUpdate(this.channel3Toggle);
		bindAndUpdate(this.channel4Toggle);
	}
}

export { ControlSettings };
