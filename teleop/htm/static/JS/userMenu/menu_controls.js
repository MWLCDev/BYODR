// Handle radio button changes
$('.channel input[type="radio"]').change(function () {
	const parent = $(this).closest('.channel');
	const channelIndex = parent.data('index') + 1;
	const value = $(this).val() === 'true';

	saveChannelState(channelIndex, value);
});
export function initDomElem() {
	updateRelayStates();
	bindSliderInputListener();
	bindBoldTextListener();
}

// Function to fetch and update relay states from the backend
function updateRelayStates() {
	$.get(`${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`, function (response) {
		const states = response['states'];
		$('.channel').each(function () {
			const index = $(this).data('index');
			const state = states[index] === true;
			$(this).find(`input[value="${state}"]`).prop('checked', true);
		});
	});
}

// Function to send the current state of a relay to the backend
function saveChannelState(channel, value) {
	const command = { channel: channel, action: value ? 'on' : 'off' };
	$.post(
		`${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`,
		JSON.stringify(command),
		function (response) {
			// Optionally handle response
			updateRelayStates(); // Refresh states after change
		},
		'json'
	);
}

// Function to update the displayed value next to the sliders
function updateSliderValue(slider) {
	const valueSpan = document.getElementById(slider.id + '-value');
	valueSpan.textContent = slider.value;
}

export function bindSliderInputListener() {
	// Add event listeners to all sliders to update their displayed values on input
	document.querySelectorAll('#input-sliders input[type="range"]').forEach(function (slider) {
		slider.addEventListener('input', function () {
			updateSliderValue(slider);
		});
	});
}

// Function to update label styles based on checkbox state
function updateLabelStyles(checkbox, labelOn, labelOff) {
	if (checkbox.checked) {
		labelOn.style.fontWeight = 'bold';
		labelOff.style.fontWeight = 'normal';
	} else {
		labelOn.style.fontWeight = 'normal';
		labelOff.style.fontWeight = 'bold';
	}
}

export function bindBoldTextListener() {
	// Get elements for channel 3
	const channel3Toggle = document.getElementById('channel3-toggle');
	const channel3LabelOn = document.getElementById('channel3-label-on');
	const channel3LabelOff = document.getElementById('channel3-label-off');

	// Get elements for channel 4
	const channel4Toggle = document.getElementById('channel4-toggle');
	const channel4LabelOn = document.getElementById('channel4-label-on');
	const channel4LabelOff = document.getElementById('channel4-label-off');

	// Add event listeners to update label styles on change
	channel3Toggle.addEventListener('change', function () {
		updateLabelStyles(channel3Toggle, channel3LabelOn, channel3LabelOff);
	});

	channel4Toggle.addEventListener('change', function () {
		updateLabelStyles(channel4Toggle, channel4LabelOn, channel4LabelOff);
	});

	// Initial update to set the correct styles based on the initial state
	updateLabelStyles(channel3Toggle, channel3LabelOn, channel3LabelOff);
	updateLabelStyles(channel4Toggle, channel4LabelOn, channel4LabelOff);
}
