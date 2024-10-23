// This file isn't used anymore

class RobotTrainSettings {
	constructor() {
		// Automatically call the method when an instance is created
		this.fetchSegmentDataAndDisplay();
		this.enableDragAndDrop();
		this.getNanoIP();
		this.setupWifiNetworksButton();
	}

	setupWifiNetworksButton() {
		const wifiButton = document.getElementById('scanWifiNetworks');
		wifiButton.addEventListener('click', () => {
			this.getWifiNetworks();
		});
	}

	async callRouterApi(action, params = {}) {
		try {
			const options = {
				method: Object.keys(params).length === 0 ? 'GET' : 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
			};

			// Add body only for POST requests
			if (options.method === 'POST') {
				options.body = JSON.stringify(params);
			}

			const response = await fetch(`/ssh/router?action=${action}`, options);
			const contentType = response.headers.get('content-type');

			if (contentType && contentType.includes('application/json')) {
				return await response.json(); // Handle JSON response
			} else {
				return await response.text(); // Handle plain text response
			}
		} catch (error) {
			console.error('Error while calling router endpoint:', error);
			return null;
		}
	}

	// Method to fetch data from the API and display it
	async fetchSegmentDataAndDisplay() {
		try {
			const response = await fetch('/teleop/robot/options');
			const jsonData = await response.json();
			console.log(jsonData);
			// Extract only the segments data
			const segmentsData = this.extractSegmentsData(jsonData);
			// Call a function to update the table with segment in robot data
			this.updateSegmentsTable(segmentsData);
		} catch (error) {
			console.error('There has been a problem with your fetch operation:', error);
		}
	}

	// Function to extract only the segments data
	extractSegmentsData(data) {
		let segmentsData = {};
		for (const key in data) {
			if (data.hasOwnProperty(key) && key.startsWith('segment_')) {
				segmentsData[key] = data[key];
			}
		}
		return segmentsData;
	}

	updateSegmentsTable(data) {
		const tbody = document.querySelector('#container_segment_table table tbody');
		tbody.innerHTML = ''; // Clear existing rows
		for (const segment in data) {
			const row = data[segment];
			const tr = document.createElement('tr');

			tr.innerHTML = `
        <td></td>
        <td>${row['position']}</td>
        <td>${row['wifi.name']}</td>
        <td><input type="radio" name="mainSegment"></td>
        <td><button type="button">X</button></td>
      `;
			tbody.appendChild(tr);
		}
	}

	async getNanoIP() {
		const data = await this.callRouterApi('get_nano_ip'); // Calls fetch_ssid function in Router class
		const showSSID = document.getElementById('dummy_text');
		// console.log(data);
		showSSID.innerHTML = data.message;
	}

	async getWifiNetworks() {
		try {
			let data = await this.callRouterApi('get_wifi_networks');

			if (typeof data === 'string') {
				data = JSON.parse(data);
			}

			const tbody = document.querySelector('#connectable_networks_table tbody');
			tbody.innerHTML = '';
			// console.log(data);
			data.forEach((network, index) => {
				const ssid = network['ESSID'];
				const mac = network['MAC'];

				const tr = document.createElement('tr');
				const button = document.createElement('button');
				button.type = 'button';
				button.textContent = 'Add';

				button.addEventListener('click', () => {
					this.callRouterApi('add_network', { ssid: ssid, mac: mac });
				});

				tr.innerHTML = `<td>${ssid}</td><td></td>`;
				tr.children[1].appendChild(button);

				// Add animation with a delay
				tr.style.animationDelay = `${index * 0.1}s`;
				tr.classList.add('fade-in-left');

				tbody.appendChild(tr);
			});
		} catch (error) {
			console.error('Error fetching WiFi networks:', error);
		}
	}

	enableDragAndDrop() {
		const tbody = document.querySelector('table tbody'); // Select only tbody
		let draggedElement = null;
		tbody.addEventListener('touchstart', (e) => handleDragStart(e.target.closest('tr')), false);
		tbody.addEventListener('touchmove', (e) => handleDragMove(e.touches[0]), false);
		tbody.addEventListener('touchend', () => handleDragEnd(), false);

		tbody.addEventListener('mousedown', (e) => handleDragStart(e.target.closest('tr')), false);
		tbody.addEventListener('mousemove', (e) => handleDragMove(e), false);
		tbody.addEventListener('mouseup', () => handleDragEnd(), false);

		function handleDragStart(row) {
			if (row && row.parentNode === tbody) {
				draggedElement = row;
				// Add a class to the dragged element for the floating effect
				draggedElement.classList.add('floating');
			}
		}

		function handleDragMove(event) {
			if (!draggedElement) return;

			const targetElement = document.elementFromPoint(event.clientX, event.clientY);
			const targetRow = targetElement?.closest('tr');

			if (targetRow && targetRow.parentNode === tbody && targetRow !== draggedElement) {
				swapRows(draggedElement, targetRow);
			}
		}

		function handleDragEnd() {
			if (draggedElement) {
				// Trigger the reverse transition for landing
				draggedElement.style.transition = 'transform 0.2s, box-shadow 0.2s';
				draggedElement.classList.remove('floating');

				// Delay the removal of inline styles to allow the transition to complete
				setTimeout(() => {
					draggedElement.style.transition = '';
					updateRowNumbers();
				}, 200); // Duration should match the CSS transition time

				draggedElement = null;
			}
		}

		function swapRows(row1, row2) {
			const parentNode = row1.parentNode;
			const nextSibling = row1.nextElementSibling === row2 ? row1 : row1.nextElementSibling;
			parentNode.insertBefore(row2, nextSibling);
		}

		function updateRowNumbers() {
			const rows = tbody.querySelectorAll('tr');
			rows.forEach((row, index) => {
				console.log('made something here');
				// Assuming the position number is in the second cell
				row.cells[1].textContent = index + 1;
			});
		}
	}
}
