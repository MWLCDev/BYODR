// robotConfiguration_b_utils.js

import RobotState from './robotConfiguration_z_state.js';

const WifiNetworkManager = (() => {
	async function fetchWifiNetworksAndPopulateTable() {
		try {
			let data = await ApiService.callRouterApi('get_wifi_networks');
			if (typeof data === 'string') {
				data = JSON.parse(data);
			}
			populateWifiNetworksTable(data);
		} catch (error) {
			console.error('Error fetching WiFi networks:', error);
		}
	}

	function populateWifiNetworksTable(networks) {
		const tbody = document.querySelector('#connectable_networks_table tbody');
		tbody.innerHTML = '';

		networks.forEach((network, index) => {
			const ssid = network['ESSID'];
			const mac = network['MAC'];
			const tr = createNetworkTableRow(ssid, index);
			const button = createAddNetworkButton();
			tr.children[1].appendChild(button);
			tbody.appendChild(tr);

			button.addEventListener('click', () => {
				PasswordModal.show(ssid, mac);
			});
		});
	}

	function createNetworkTableRow(ssid, index) {
		const tr = document.createElement('tr');
		tr.innerHTML = `<td>${ssid}</td><td></td>`;
		tr.style.animationDelay = `${index * 0.1}s`;
		tr.classList.add('fade-in-left');
		return tr;
	}

	function createAddNetworkButton() {
		const button = document.createElement('button');
		button.type = 'button';
		button.textContent = 'Add';
		return button;
	}

	return {
		fetchWifiNetworksAndPopulateTable,
	};
})();

const SegmentManager = (() => {
	function addNetworkToSegments(ssid, mac) {
		let segments = RobotState.segmentsData || {};
		let newIndex = getNextSegmentIndex(segments);
		const newSegment = createSegment(ssid, mac, newIndex);
		const updatedSegments = { ...segments, [`segment_${newIndex}`]: newSegment };
		RobotState.segmentsData = updatedSegments;
	}

	function getNextSegmentIndex(segments) {
		let newIndex = 1;
		while (segments[`segment_${newIndex}`]) {
			newIndex++;
		}
		return newIndex;
	}

	function createSegment(ssid, mac, newIndex) {
		return {
			'ip.number': '',
			'wifi.name': ssid,
			'mac.address': mac,
			'vin.number': '',
			position: newIndex,
			host: 'False',
		};
	}

	function removeSegment(segName) {
		// Iterate over each segment to find the one with the matching name
		for (const key in RobotState.segmentsData) {
			if (RobotState.segmentsData.hasOwnProperty(key)) {
				const segment = RobotState.segmentsData[key];
				if (segment['wifi.name'] === segName) {
					// Delete the segment from the data
					delete RobotState.segmentsData[key];

					// Reorganize the remaining segments if needed
					reorganizeSegments();
					return;
				}
			}
		}

		console.log(`Segment with name ${segName} not found.`);
	}

	// Function to reorganize segments after deletion
	function reorganizeSegments() {
		const newSegmentData = {};
		let newIndex = 1;
		for (const key in RobotState.segmentsData) {
			if (RobotState.segmentsData.hasOwnProperty(key)) {
				newSegmentData[`segment_${newIndex}`] = RobotState.segmentsData[key];
				newIndex++;
			}
		}
		RobotState.segmentsData = newSegmentData;
	}

	/**
	 * Main function that orchestrates the updating of segment positions in the table
	 * and synchronizes these updates with the RobotState.segmentsData.
	 */
	function updatePositionIndices() {
		const rows = document.querySelectorAll('#segment_table tbody tr');

		updatePositionsInData(rows);
		const sortedSegments = collectAndSortSegments();
		const renamedSegments = renameSegmentKeys(sortedSegments);
		removeAllSegments();
		reAddSegments(renamedSegments);
	}

	/**
	 * Updates the positions of segments in the RobotState.segmentsData based on the
	 * current order of rows in the table.
	 * @param {NodeListOf<HTMLTableRowElement>} rows - The rows of the table.
	 */
	function updatePositionsInData(rows) {
		rows.forEach((row, index) => {
			const wifiNameCell = row.cells[2];
			const wifiName = wifiNameCell.textContent;
			const positionCell = row.cells[1];
			if (positionCell) {
				positionCell.textContent = index + 1;
			}

			for (let segment in RobotState.segmentsData) {
				if (RobotState.segmentsData[segment]['wifi.name'] === wifiName) {
					RobotState.segmentsData[segment].position = index + 1;
					break;
				}
			}
		});
	}

	/**
	 * Collects all segments from RobotState.segmentsData, sorts them based on their
	 * updated position, and returns the sorted array.
	 * @returns {Array} An array of sorted segments.
	 */
	function collectAndSortSegments() {
		let updatedSegments = [];
		for (let segment in RobotState.segmentsData) {
			if (segment.startsWith('segment_')) {
				updatedSegments.push({ key: segment, data: RobotState.segmentsData[segment] });
			}
		}
		return updatedSegments.sort((a, b) => a.data.position - b.data.position);
	}

	/**
	 * Renames the keys of the segment objects to match their position in the sorted array.
	 * @param {Array} segments - The array of segments to rename.
	 * @returns {Array} An array of segments with updated keys.
	 */
	function renameSegmentKeys(segments) {
		return segments.map((segment, index) => ({
			key: `segment_${index + 1}`,
			data: segment.data,
		}));
	}

	/**
	 * Removes all segments from RobotState.segmentsData that start with "segment_".
	 */
	function removeAllSegments() {
		Object.keys(RobotState.segmentsData)
			.filter((key) => key.startsWith('segment_'))
			.forEach((segKey) => removeSegment(RobotState.segmentsData[segKey]['wifi.name']));
	}

	/**
	 * Adds the given segments back into RobotState.segmentsData.
	 * @param {Array} segments - The array of segments to be re-added.
	 */
	function reAddSegments(segments) {
		segments.forEach((segment) => {
			RobotState.segmentsData[segment.key] = segment.data;
		});
	}

	return {
		addNetworkToSegments,
		removeSegment,
		reorganizeSegments,
		updatePositionIndices,
	};
})();

const ApiService = (() => {
	async function callRouterApi(action, params = {}) {
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

	async function postConfigData(data) {
		return fetch('/teleop/send_config', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(data),
		});
	}

	async function getNanoIP() {
		const data = await callRouterApi('get_nano_ip');
		const showSSID = document.getElementById('dummy_text');
		showSSID.innerHTML = data.message;
	}

	return {
		callRouterApi,
		postConfigData,
		getNanoIP,
	};
})();

const Utils = (() => {
	function showToast(message) {
		const toast = document.createElement('div');
		toast.textContent = message;
		toast.style.position = 'fixed';
		toast.style.bottom = '10px';
		toast.style.left = '50%';
		toast.style.transform = 'translateX(-50%)';
		toast.style.backgroundColor = 'black';
		toast.style.color = 'white';
		toast.style.padding = '10px';
		toast.style.borderRadius = '7px';
		toast.style.zIndex = '1000';

		document.body.appendChild(toast);

		setTimeout(() => {
			toast.remove();
		}, 3000);
	}

	function generatePassword(ssid) {
		const networkParts = ssid.split('_');
		const suffix = networkParts[1]; // part after '_'
		// Find the first alphabetic character in the suffix
		const firstChar = suffix.match(/[A-Za-z]/) ? suffix.match(/[A-Za-z]/)[0] : null;
		// Extract the digit (if any) in the suffix
		const digitInName = parseInt(suffix.match(/\d+/), 10); // extract digits

		if (firstChar) {
			const position = firstChar.toUpperCase().charCodeAt(0) - 'A'.charCodeAt(0) + 1;

			// Only return the pre-generated password if the digit matches the letter position
			if (digitInName === position) {
				return `voiarcps1n${position}`; // Valid password
			}
		}

		return null; // Show empty if there's no valid match
	}

	return {
		showToast,
		generatePassword,
	};
})();

const PasswordModal = (() => {
	let modal;
	let elPasswordInput;
	let elNetworkNameSpan;
	let elConfirmButton;
	let closeBtn;
	let cancelButton;

	function init() {
		// Access DOM elements inside the init function
		modal = document.getElementById('passwordModal');
		elPasswordInput = modal.querySelector('#password-input');
		elNetworkNameSpan = modal.querySelector('#network-name');
		elConfirmButton = modal.querySelector('#confirm-password-button');
		closeBtn = modal.querySelector('#password-modal-close');
		cancelButton = modal.querySelector('#cancel-button');

		// Close the modal when the X button is clicked
		closeBtn.onclick = hidePasswordPrompt;

		// Close the modal if the user clicks outside of it
		window.onclick = (event) => {
			if (event.target === modal) {
				hidePasswordPrompt();
			}
		};

		// Handle the confirmation of the password
		elConfirmButton.addEventListener('click', () => {
			const password = elPasswordInput.value;
			if (password) {
				const ssid = elNetworkNameSpan.textContent;
				const mac = elConfirmButton.dataset.mac; // store mac in dataset
				handleNetworkAddition(ssid, mac, password);
				hidePasswordPrompt();
			}
		});

		// Close modal on cancel
		cancelButton.addEventListener('click', hidePasswordPrompt);

		// Disable the confirm button initially if password is empty
		elPasswordInput.addEventListener('input', () => {
			elConfirmButton.disabled = !elPasswordInput.value;
		});
	}

	function show(ssid, mac) {
		const generatedPassword = Utils.generatePassword(ssid);
		elPasswordInput.value = generatedPassword || '';
		elNetworkNameSpan.textContent = ssid;
		elConfirmButton.dataset.mac = mac;

		// Show the modal
		showPasswordPrompt();

		// Disable the confirm button if password is empty
		elConfirmButton.disabled = !elPasswordInput.value;
	}

	function showPasswordPrompt() {
		modal.classList.add('show');
		modal.style.display = 'block'; // Ensure it becomes visible
	}

	function hidePasswordPrompt() {
		modal.classList.remove('show');
		modal.style.display = 'none'; // Ensure it hides
	}

	function handleNetworkAddition(ssid, mac, password) {
		SegmentManager.addNetworkToSegments(ssid, mac);
		ApiService.callRouterApi('add_network', { ssid, mac, password });
		updateSegmentsTable();
	}

	return {
		init,
		show,
	};
})();

export { ApiService, PasswordModal, SegmentManager, Utils, WifiNetworkManager };
