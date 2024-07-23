// Initialize settings content
export function initializeSettings() {
	fetchUserSettings();
}

// Fetch user settings from backend and generate form inputs
function fetchUserSettings() {
	fetch('/teleop/user/options')
		.then((response) => response.json())
		.then((settings) => {
			const form = document.getElementById('form_user_options');
			form.innerHTML = ''; // Clear existing form content
			Object.entries(settings).forEach(([section, options]) => {
				const fieldset = document.createElement('fieldset');
				const legend = document.createElement('legend');
				legend.textContent = section;
				fieldset.appendChild(legend);

				Object.entries(options).forEach(([name, value]) => {
					const input = document.createElement('input');
					// Bool values are case sensitive between js and python
					input.type = value === 'True' || value === 'False' ? 'checkbox' : 'text';
					input.name = name;
					if (value === 'True' || value === 'False') {
						input.checked = value === 'true';
					} else {
						input.value = value;
					}

					const label = document.createElement('label');
					label.textContent = name;
					label.appendChild(input);

					const div = document.createElement('div');
					div.appendChild(label);
					fieldset.appendChild(div);
				});

				form.appendChild(fieldset);
			});
			document.getElementById('submit_save_apply').disabled = true; // Disable save button initially
		});
}

// Save settings to backend
function saveSettings() {
	const inputs = document.querySelectorAll('#form_user_options input');
	const settings = Array.from(inputs).reduce((acc, input) => {
		const isChanged = input.type === 'checkbox' ? input.checked.toString() !== input.defaultChecked.toString() : input.value !== input.defaultValue;
		if (isChanged) {
			acc[input.name] = input.type === 'checkbox' ? input.checked : input.value;
		}
		return acc;
	}, {});

	if (Object.keys(settings).length === 0) {
		alert('No changes to save.');
		return;
	}

	fetch('/teleop/user/options', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(settings),
	})
		.then((response) => {
			if (response.ok) {
				alert('Settings saved successfully.');
				document.getElementById('submit_save_apply').disabled = true; // Disable button after successful save
				fetchUserSettings(); // Refresh settings form
			} else {
				throw new Error('Failed to save settings');
			}
		})
		.catch((error) => {
			alert('Error saving settings: ' + error.message);
		});
}

// Set up event handlers only if the elements exist on the page
document.addEventListener('DOMContentLoaded', () => {
  const submitButton = document.getElementById('submit_save_apply');
  const form = document.getElementById('form_user_options');

  if (submitButton) {
      submitButton.addEventListener('click', saveSettings);
  }

  if (form) {
      form.addEventListener('input', () => {
          if (submitButton) {
              submitButton.disabled = false; // Enable save button on change
          }
      });
  }
});
