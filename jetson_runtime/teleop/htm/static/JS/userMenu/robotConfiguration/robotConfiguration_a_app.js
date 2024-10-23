// robotConfiguration_a_main.js
import { ApiService, PasswordModal, SegmentManager, Utils, WifiNetworkManager } from './robotConfiguration_b_utils.js';

import { fetchSegmentDataAndDisplay, setupRemoveSegmentButtonListener } from './robotConfiguration_c_table_robot.js';

// This file now focuses on DOM elements and linking functions between components and utilities
class RobotTrainSettings {
	constructor() {
		this.setupButtons();

		// Initialize network and segment data
		ApiService.getNanoIP();
		fetchSegmentDataAndDisplay();
		WifiNetworkManager.fetchWifiNetworksAndPopulateTable();

		// Initialize the password modal functionality
		PasswordModal.init();
	}

	// Setup the button event listeners
	setupButtons() {
		this.setupTestConfigButton();
		setupRemoveSegmentButtonListener(); // Imported from utils
	}

	setupTestConfigButton() {
		const testData = document.getElementById('test_config');
		testData.addEventListener('click', () => {
			sendRobotConfig(); // Need to import sendRobotConfig from the appropriate module
		});
	}
}

export { RobotTrainSettings };
