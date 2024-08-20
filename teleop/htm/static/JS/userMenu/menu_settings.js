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
  
	populateForm(settings) {
		this.form.innerHTML = '';
		Object.entries(settings).forEach(([section, options]) => {
			const fieldset = document.createElement('fieldset');
			const legend = document.createElement('legend');
			legend.textContent = section.charAt(0).toUpperCase() + section.slice(1);
			fieldset.appendChild(legend);

			Object.entries(options).forEach(([name, value]) => {
				// Skip specific fields as they are already in the relay settings menu
				if (section === 'vehicle' && (name === 'ras.driver.steering.offset' || name === 'ras.driver.motor.scale')) return;

				const input = document.createElement('input');
				input.type = value === 'true' || value === 'false' ? 'checkbox' : 'text';
				input.name = this.filterFieldName(section, name); // Use the transformed name
				input.dataset.originalKey = name; // Store the original key without applying filters
				input.dataset.section = section; // Store the section name in dataset
				input.disabled = true; // Initially disable input fields

				if (value === 'true' || value === 'false') {
					input.checked = value === 'true';
				} else {
					input.value = value;
				}

				const displayName = this.filterFieldName(section, name);

				const label = document.createElement('label');
				label.textContent = displayName.charAt(0).toUpperCase() + displayName.slice(1) + ':';
				label.appendChild(input);

				const div = document.createElement('div');
				div.appendChild(label);
				fieldset.appendChild(div);
			});

			this.form.appendChild(fieldset);
		});
	}

	filterFieldName(section, name) {
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

	saveSettings() {
		const sections = {}; // Hold the structured settings

		const inputs = this.form.querySelectorAll('input');

		// Iterate through the inputs and organize them by section
		inputs.forEach((input) => {
			const originalKey = input.dataset.originalKey;
			const section = input.dataset.section;

			if (!sections[section]) {
				sections[section] = []; // Initialize the section as an array if it doesn't exist
			}

			// Convert the value to a string before saving it. This is how the backend expects them
			const value = input.type === 'checkbox' ? String(input.checked) : String(input.value);

			// Save the key-value pair as an array (tuple-like) in the correct section
			sections[section].push([originalKey, value]);
		});

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

// Initialize the UserSettingsManager class
export { UserSettingsManager };
