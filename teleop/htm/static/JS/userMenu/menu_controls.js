class ControlSettings {
	constructor() {
		this.scaleInput = $('#scale_input');
		this.offsetInput = $('#offset_input');
		this.deadZoneInput = $('#dead_zone_input');

		this.scaleInputText = $('#scale_input_value');
		this.offsetInputText = $('#offset_input_value');
		this.deadZoneInputText = $('#dead_zone_width_value');

		this.initDomElements();
	}

	initDomElements() {
		this.fetchRoverData();
		this.bindSliderInputListeners();
		this.bindBoldTextListeners();
		this.updateRelayStates();
	}

	bindSliderInputListeners() {
		// Bindings for scale and offset inputs
		this.scaleInput.on('input', () => {
			this.scaleInputText.text(this.scaleInput.val());
		});
		this.offsetInput.on('input', () => {
			this.offsetInputText.text(this.offsetInput.val());
		});

		// Binding for dead zone input
		this.deadZoneInput.on('input', () => {
			this.deadZoneInputText.text(this.deadZoneInput.val());
		});

		// Post data on 'change' event
		this.scaleInput
			.add(this.offsetInput)
			.add(this.deadZoneInput)
			.on('change', () => {
				this.sendDataToBackend();
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

	sendDataToBackend() {
		let data = {
			vehicle: [
				['ras.driver.motor.scale', this.scaleInput.val()],
				['ras.driver.steering.offset', this.offsetInput.val()],
				['ras.driver.deadzone.width', this.deadZoneInput.val()],
			].filter((setting) => setting[1] !== ''),
		};

		$.ajax({
			url: '/teleop/user/options',
			method: 'POST',
			contentType: 'application/json',
			data: JSON.stringify(data),
			error: (error) => console.error('Error:', error),
		});
	}

	updateRelayStates() {
		$.get(`${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`)
			.done((response) => {
				$('.channel').each(function () {
					const index = $(this).data('index');
					const state = response.states[index] === true;
					$(this).find(`input[value="${state}"]`).prop('checked', state);
				});
			})
			.fail((error) => console.error('Error updating relay states:', error));
	}

	bindBoldTextListeners() {
		// General function to bind and update label styles
		const bindAndUpdate = (toggle, labelOn, labelOff) => {
			toggle
				.on('change', () => {
					this.updateLabelStyles(toggle[0], labelOn[0], labelOff[0]);
				})
				.trigger('change');
		};

		bindAndUpdate($('#channel3-toggle'), $('#channel3-label-on'), $('#channel3-label-off'));
		bindAndUpdate($('#channel4-toggle'), $('#channel4-label-on'), $('#channel4-label-off'));
	}

	updateLabelStyles(checkbox, labelOn, labelOff) {
		if (checkbox.checked) {
			labelOn.style.fontWeight = 'bold';
			labelOff.style.fontWeight = 'normal';
		} else {
			labelOn.style.fontWeight = 'normal';
			labelOff.style.fontWeight = 'bold';
		}
	}
}

export { ControlSettings };
