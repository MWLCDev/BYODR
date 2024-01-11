class RobotMenu {
  constructor() {
    this.robotUtils = new RobotUtils()
    new SegmentTableManager(this, this.robotUtils);
    this.getNanoIP();
    this.setupWifiNetworksButton();
  }

  showSegments() {
    console.log(this.robotUtils.segmentsData);
  }


  setupWifiNetworksButton() {
    const wifiButton = document.getElementById('scan_wifi_networks');
    wifiButton.addEventListener('click', () => {
      // Disable the button and set a timer to re-enable it
      wifiButton.disabled = true;
      this.robotUtils.showToast('please wait to try again');

      this.getWifiNetworks()
        .then(() => {
          // Re-enable the button after the data is processed
          wifiButton.disabled = false;
        })
        .catch(() => {
          // Re-enable the button in case of an error
          wifiButton.disabled = false;
        });
    });
  }

  async getNanoIP() {
    const data = await this.robotUtils.callRouterApi('get_nano_ip'); // Calls fetch_ssid function in Router class
    const showSSID = document.getElementById('dummy_text');
    console.log(data);
    showSSID.innerHTML = data.message;
  }

  async getWifiNetworks() {
    try {
      let data = await this.robotUtils.callRouterApi('get_wifi_networks');

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
        button.addEventListener('click', () => {
          this.addNetworkToSegments(ssid, mac);

        });
      });
    } catch (error) {
      console.error('Error fetching WiFi networks:', error);
    }
  }

  // Function to add network to segmentsData
  addNetworkToSegments(ssid, mac) {

    let segments = this.robotUtils.segmentsData || {};
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
      "position": "",
      "main": "False",
    };

    this.robotUtils.segmentsData = { [`segment_${newIndex}`]: newSegment };
    console.log(this.robotUtils.segmentsData)
  }



  updatePositionIndices() {
    const rows = document.querySelectorAll('#segment_table tbody tr');
    rows.forEach((row, index) => {
      const positionCell = row.cells[1];
      if (positionCell) {
        positionCell.textContent = index + 1; // +1 because indices are 0-based
      }
    });
  }


}
class RobotUtils {

  /**
   * Add one data entry to the list of segments
   */
  set segmentsData(newData) {
    // Check if newData is already in _segmentsData
    for (const key in this._segmentsData) {
      if (this._segmentsData.hasOwnProperty(key)) {
        const existingSegment = this._segmentsData[key];
        const newSegment = newData[Object.keys(newData)[0]]; // Assuming newData contains only one segment to add

        if (existingSegment['wifi.name'] === newSegment['wifi.name'] &&
          existingSegment['mac.address'] === newSegment['mac.address']) {
          console.log('This network is already added.');
          return;
        }
      }
    }

    // If the new data is not already in _segmentsData, add it
    this._segmentsData = { ...this._segmentsData, ...newData };
  }


  get segmentsData() {
    return this._segmentsData;
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

  showToast(message) {
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
    }, 3000); // Remove the toast after 3 seconds
  }
}

class SegmentTableManager {
  constructor(robotMenu, robotUtils) {
    this.robotMenu = robotMenu;
    this.robotUtils = robotUtils;
    this.tbody = document.querySelector('#segment_table tbody');
    this.draggedElement = null;
    // Initialize both main functionalities
    this.enableDragAndDrop();
    this.fetchSegmentDataAndDisplay();
  }



  // Method to fetch data from the API and display it
  async fetchSegmentDataAndDisplay() {
    try {
      const response = await fetch('/teleop/robot/options');
      const jsonData = await response.json();
      // Extract only the segments data
      this.robotUtils.segmentsData = this.extractSegmentsData(jsonData);
      this.robotMenu.showSegments()
      // Call a function to update the table with segment in robot data
      this.updateSegmentsTable();
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

  // Function to update the table with segments data
  updateSegmentsTable() {
    const tbody = document.querySelector('#container_segment_table table tbody');
    tbody.innerHTML = '';
    for (const segment in this.robotUtils.segmentsData) {
      const row = this.robotUtils.segmentsData[segment];
      const tr = document.createElement('tr');

      // Check if the 'main' value is true and set the radio button accordingly
      const isMainSegment = row['main'] === 'True';

      tr.innerHTML = `
        <td></td>
        <td></td>
        <td>${row['wifi.name']}</td>
        <td><input type="radio" name="mainSegment" ${isMainSegment ? 'checked' : ''}></td>
        <td><button type="button">X</button></td>
      `;
      tbody.appendChild(tr);
    }
    this.robotMenu.updatePositionIndices();
  }

  enableDragAndDrop() {
    this.robotMenu.updatePositionIndices();
    // Adding touch and mouse events to the tbody
    this.tbody.addEventListener('touchstart', (e) => this.handleDragStart(e), false);
    this.tbody.addEventListener('touchmove', (e) => this.handleDragMove(e.touches[0]), false);
    this.tbody.addEventListener('touchend', () => this.handleDragEnd(), false);
    this.tbody.addEventListener('mousedown', (e) => this.handleDragStart(e), false);
    this.tbody.addEventListener('mousemove', (e) => this.handleDragMove(e), false);
    this.tbody.addEventListener('mouseup', () => this.handleDragEnd(), false);
  }

  handleDragStart(event) {
    if (event.target === event.target.closest('tr').firstElementChild) {
      const row = event.target.closest('tr');
      if (row && row.parentNode === this.tbody) {
        this.draggedElement = row;
        this.draggedElement.classList.add('floating');
      }
    }
  }

  handleDragMove(event) {
    if (!this.draggedElement) return;

    const targetElement = document.elementFromPoint(event.clientX, event.clientY);
    const targetRow = targetElement?.closest('tr');

    if (targetRow && targetRow.parentNode === this.tbody && targetRow !== this.draggedElement) {
      // Use this.tbody here
      this.swapRows(this.draggedElement, targetRow);
    }
  }

  handleDragEnd() {
    if (this.draggedElement) {
      // Ensure that this.draggedElement is a valid DOM element
      if (this.draggedElement instanceof HTMLElement) {
        this.draggedElement.style.transition = 'transform 0.2s, box-shadow 0.2s';
        this.draggedElement.classList.remove('floating');
        setTimeout(() => {
          if (this.draggedElement instanceof HTMLElement) {
            this.draggedElement.style.transition = '';
          }
        }, 200);
      }

      this.draggedElement = null;

      // Call updatePositionIndices after a row has been repositioned
      this.robotMenu.updatePositionIndices();
    }
  }

  swapRows(row1, row2) {
    const parentNode = row1.parentNode;
    const nextSibling = row1.nextElementSibling === row2 ? row1 : row1.nextElementSibling;
    parentNode.insertBefore(row2, nextSibling);
  }

}
