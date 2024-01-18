import { callRouterApi } from "./robotConfiguration_b_utils.js"
import { enableDragAndDrop, fetchSegmentDataAndDisplay, addNewRow } from "./robotConfiguration_c_table_robot.js"
import RobotState from "./robotConfiguration_z_state.js"

class RobotMenu {
  constructor() {
    this.getNanoIP();
    this.setupButtons();
    enableDragAndDrop();
    fetchSegmentDataAndDisplay();
  }

  setupButtons() {
    const saveTablesData = document.getElementById('Add_row');
    saveTablesData.addEventListener('click', () => {
      addNewRow()
    });
    const testData = document.getElementById('test_config');
    testData.addEventListener('click', () => {
      this.send_config()
    });
  }

  async send_config() {
    const dataToSend = RobotState.segmentsData;
    console.log(dataToSend)
    try {
      const response = await fetch('/teleop/send_config', {
        method: 'POST', // Specify the method
        headers: {
          'Content-Type': 'application/json' // Specify the content type
        },
        body: JSON.stringify(dataToSend) // Convert the data to a JSON string
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const responseData = await response.json();
      console.log('Response from server:', responseData);
    } catch (error) {
      console.error('Error while sending configuration:', error);
    }

  }

  async getNanoIP() {
    const data = await callRouterApi('get_nano_ip'); // Calls fetch_ssid function in Router class
    const showSSID = document.getElementById('dummy_text');
    showSSID.innerHTML = data.message;
  }
  addNetworkToSegments(ssid, mac) {
    let segments = RobotState.segmentsData || {};
    let newIndex = 1;
    while (segments[`segment_${newIndex}`]) {
      newIndex++;
    }

    // Create new segment
    const newSegment = {
      "ip.number": "",
      "wifi.name": ssid,
      "mac.address": mac,
      "vin.number": "",
      "position": newIndex,
      "host": "False",
    };

    // Prepare the new segments data, including the new segment
    const updatedSegments = { ...segments, [`segment_${newIndex}`]: newSegment };

    // Update segments data using the setter
    RobotState.segmentsData = updatedSegments;
  }

}

window.RobotMenu = RobotMenu;

