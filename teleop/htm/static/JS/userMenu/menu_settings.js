class UserSettingsManager {
	constructor() {
		this.form = document.getElementById('form_user_options');
		this.editButton = document.getElementById('edit_button');
		this.saveButton = document.getElementById('submit_save_apply');
		this.fetchUserSettings();
		this.disableFormInputs();
		this.init();
	}

	init() {
		if (this.editButton) {
			this.editButton.addEventListener('click', () => this.enableEditMode());
		}

		if (this.saveButton) {
			this.saveButton.addEventListener('click', () => this.saveSettings());
		}

		this.form.addEventListener('input', () => {
			if (this.saveButton) {
				this.saveButton.disabled = false;
			}
		});

		this.saveButton.style.display = 'none';
	}

	fetchUserSettings() {
		fetch('/teleop/user/options')
			.then((response) => response.json())
			.then((settings) => {
				this.populateForm(settings);
			})
			.catch((error) => alert('Error fetching settings: ' + error.message));
	}

	// Populate form with fetched settings
	populateForm(settings) {
		this.form.innerHTML = '';

		Object.entries(settings).forEach(([section, options]) => {
			const fieldset = this.createFieldset(section);

			Object.entries(options).forEach(([name, value]) => {
				if (this.shouldSkipField(section, name)) return;

				const input = this.createInput(section, name, value);
				const label = this.createLabel(section, name, input);

				const div = document.createElement('div');
				div.appendChild(label);
				fieldset.appendChild(div);
			});

			this.form.appendChild(fieldset);
		});
	}

	// Create a fieldset with a legend for each section
	createFieldset(section) {
		const fieldset = document.createElement('fieldset');
		const legend = document.createElement('legend');
		legend.textContent = section.charAt(0).toUpperCase() + section.slice(1);
		fieldset.appendChild(legend);
		return fieldset;
	}

	// Determine whether to skip certain fields
	shouldSkipField(section, name) {
		return section === 'vehicle' && ['ras.driver.steering.offset', 'ras.driver.motor.scale', 'ras.driver.deadzone.width'].includes(name);
	}

	// Create an input element based on the value or specific field name
	createInput(section, name, value) {
		const isCheckbox = value === 'true' || value === 'false' || name === 'ras.driver.motor.alternate';
		const input = document.createElement('input');
		input.type = isCheckbox ? 'checkbox' : 'text';
		input.name = this.filterFieldName(section, name); // Use the transformed name
		input.dataset.originalKey = name; // Store the original key without applying filters
		input.dataset.section = section; // Store the section name in dataset
		input.disabled = true; // Initially disable input fields

		if (isCheckbox) {
			input.checked = value === 'true';
		} else {
			input.value = value;
		}
		return input;
	}

	// Create a label for the input element
	createLabel(section, name, input) {
		const displayName = this.filterFieldName(section, name);
		const label = document.createElement('label');
		label.textContent = displayName.charAt(0).toUpperCase() + displayName.slice(1) + ':';
		label.appendChild(input);
		return label;
	}

	filterFieldName(section, name) {
		console.log(section, name);
		if (section === 'camera') {
			name = name.replace('ip', 'IP');
		} else if (section === 'pilot') {
			name = name.replace('driver.', '').replace('cc.', '').replace('throttle.', '');
			if (name.includes('pid')) name = name.slice(0, -1) + name.slice(-1).toUpperCase();
		} else if (section === 'vehicle') {
			if (name.includes('ras.master.uri')) name = name.replace('ras.master.uri', 'Pi URI');
			else if (name.includes('gps')) name = name.replace('gps', 'GPS');
			else if (name.includes('ras.driver.')) name = name.replace('ras.driver.', '');
		}
		return name.replace(/[._]/g, ' ');
	}

	// Save settings to the backend
	saveSettings() {
		const sections = this.collectFormData();

		fetch('/teleop/user/options', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(sections),
		})
			.then((response) => {
				if (response.ok) {
					alert('Settings saved successfully.');
					this.disableFormInputs();
					this.editButton.style.display = 'block';
					this.saveButton.style.display = 'none';
				} else {
					throw new Error('Failed to save settings');
				}
			})
			.catch((error) => {
				alert('Error saving settings: ' + error.message);
			});
	}

	// Collect data from the form inputs
	collectFormData() {
		const sections = {};
		const inputs = this.form.querySelectorAll('input');

		inputs.forEach((input) => {
			const originalKey = input.dataset.originalKey;
			const section = input.dataset.section;

			if (!sections[section]) {
				sections[section] = [];
			}
			// Convert the value to a lowercase string for boolean values
			const value = input.type === 'checkbox' ? String(input.checked).toLowerCase() : String(input.value);
			// Save the key-value pair as an array (tuple-like) in the correct section
			sections[section].push([originalKey, value]);
		});

		return sections;
	}

	enableEditMode() {
		this.enableFormInputs();
		this.editButton.style.display = 'none';
		this.saveButton.style.display = 'block';
		this.saveButton.disabled = true; // Disable save button initially until changes are made
	}

	disableFormInputs() {
		const inputs = this.form.querySelectorAll('input');
		inputs.forEach((input) => (input.disabled = true));
	}

	enableFormInputs() {
		const inputs = this.form.querySelectorAll('input');
		inputs.forEach((input) => (input.disabled = false));
	}
}

export { UserSettingsManager };
