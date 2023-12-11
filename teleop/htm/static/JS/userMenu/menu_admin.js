class AdminMenu {
  constructor() {
    // Automatically call the method when an instance is created
    this.enableDragAndDrop();
    // this.fetchDataAndDisplay();
    // this.getSSID();
    this.getWifiNetworks();
  }
  // Method to fetch data from the API and display it
  async fetchDataAndDisplay() {
    try {
      console.log("hi")
      const response = await fetch('/teleop/robot/options');
      const jsonData = await response.json();

      // Call a function to update the table with segment in robot data
      console.log(jsonData);
      this.updateTable(jsonData);
    } catch (error) {
      console.error('There has been a problem with your fetch operation:', error);
    }
  }

  updateTable(data) {
    const tbody = document.querySelector('#container_segment_table table tbody');
    tbody.innerHTML = ''; // Clear existing rows
    for (const segment in data) {
      const row = data[segment];
      const tr = document.createElement('tr');

      tr.innerHTML = `
        <td> </td>
        <td>${row.position}</td>
        <td>${row['wifi.name']}</td>
        <td>${row['ip.number']}</td>
      `;

      tbody.appendChild(tr);
    }
  }

  async callRouterApi(action) {
    try {
      const response = await fetch(`/ssh/router?action=${action}`);
      const contentType = response.headers.get("content-type");

      if (contentType && contentType.includes("application/json")) {
        return await response.json(); // Handle JSON response
      } else {
        return await response.text(); // Handle plain text response
      }
    } catch (error) {
      console.error('Error while calling router endpoint:', error);
      return null;
    }
  }

  async getSSID() {
    const data = await this.callRouterApi("fetch_ssid"); // Calls fetch_ssid function in Router class
    const showSSID = document.getElementById("dummy_text");
    showSSID.innerHTML = data

  }

  async getWifiNetworks() {
    try {
      let data = await this.callRouterApi("get_wifi_networks");

      // Parse data if it's a string
      if (typeof data === 'string') {
        data = JSON.parse(data);
      }

      const tbody = document.querySelector('#connectable_networks_table tbody');

      // Clear existing content only after successful data retrieval
      tbody.innerHTML = '';

      data.forEach(network => {
        const ssid = network['ESSID'];
        const mac = network['MAC']; // Assuming you treat MAC as IP for display

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${ssid}</td>
          <td><button type="button">Add</button></td>
        `;
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
      if (row && row.parentNode === tbody) { // Ensure the row is part of tbody
        draggedElement = row;
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
        // Update row numbers after dragging ends
        updateRowNumbers();
      }
      draggedElement = null;
    }

    function swapRows(row1, row2) {
      const parentNode = row1.parentNode;
      const nextSibling = row1.nextElementSibling === row2 ? row1 : row1.nextElementSibling;
      parentNode.insertBefore(row2, nextSibling);
    }

    function updateRowNumbers() {
      const rows = tbody.querySelectorAll('tr');
      rows.forEach((row, index) => {
        // Assuming the position number is in the second cell
        row.cells[1].textContent = index + 1;
      });
    }
  }
}