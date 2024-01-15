import { callRouterApi, showToast } from "./robotConfiguration_b_utils.js"
import { enableDragAndDrop, fetchSegmentDataAndDisplay, updateSegmentsTable } from "./robotConfiguration_c_table_robot.js"
import RobotState from "./robotConfiguration_z_state.js"

class RobotMenu {
  constructor() {
    this.getNanoIP();
    this.setupButtons();
    enableDragAndDrop();
    fetchSegmentDataAndDisplay();
  }

  setupButtons() {
    const wifiButton = document.getElementById('scan_wifi_networks');
    wifiButton.addEventListener('click', () => {
      wifiButton.disabled = true;
      showToast('please wait to try again');

      this.getWifiNetworks()
        .then(() => {
          wifiButton.disabled = false;
        })
        .catch(() => {
          // Re-enable the button in case of an error
          wifiButton.disabled = false;
        });
    });
    const saveTablesData = document.getElementById('save_config');
    saveTablesData.addEventListener('click', () => {
      this.compareData()
    });
  }


  async getNanoIP() {
    const data = await callRouterApi('get_nano_ip'); // Calls fetch_ssid function in Router class
    const showSSID = document.getElementById('dummy_text');
    // console.log(data);
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
      console.log(data);

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
        // REFRESH THE SEGMENTS TABLE AFTER THE CLICK IS DONE 
        button.addEventListener('click', () => {
          this.addNetworkToSegments(ssid, mac);
          updateSegmentsTable()

        });

      });
    } catch (error) {
      console.error('Error fetching WiFi networks:', error);
    }
  }

  // Function to add network to segmentsData
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
      "main": "False",
    };

    // Prepare the new segments data, including the new segment
    const updatedSegments = { ...segments, [`segment_${newIndex}`]: newSegment };

    // Update segments data using the setter
    RobotState.segmentsData = updatedSegments;
  }

}

window.RobotMenu = RobotMenu;

