import { callRouterApi, removeSegment } from "./robotConfiguration_b_utils.js"
import { enableDragAndDrop, fetchSegmentDataAndDisplay, updateSegmentsTable } from "./robotConfiguration_c_table_robot.js"
import RobotState from "./robotConfiguration_z_state.js"

class RobotMenu {
  constructor() {
    this.getNanoIP();
    this.setupButtons();
    enableDragAndDrop();
    fetchSegmentDataAndDisplay();
    this.getWifiNetworks()
  }

  setupButtons() {
    const testData = document.getElementById('test_config');
    testData.addEventListener('click', () => {
      this.send_config();
    });

    // Attach the click event listener for dynamically created 'Remove' buttons
    document.addEventListener('click', (e) => {
      if (e.target.matches('#segment_table tbody button[data-wifiname]')) {
        const wifiName = e.target.getAttribute('data-wifiname');
        removeSegment(wifiName);
        updateSegmentsTable()
      }
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

  async getWifiNetworks() {
    try {
      let data = await callRouterApi('get_wifi_networks');

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

        tr.innerHTML = `<td>${ssid}</td><td></td>`;
        tr.children[1].appendChild(button);

        // Add animation with a delay
        tr.style.animationDelay = `${index * 0.1}s`;
        tr.classList.add('fade-in-left');

        tbody.appendChild(tr);

        // Add click event listener to the button
        button.addEventListener('click', () => {
          this.addNetworkToSegments(ssid, mac);
          updateSegmentsTable()
        });

      });
    } catch (error) {
      console.error('Error fetching WiFi networks:', error);
    }
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

