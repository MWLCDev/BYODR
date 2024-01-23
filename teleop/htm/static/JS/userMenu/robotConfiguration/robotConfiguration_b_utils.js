import RobotState from "./robotConfiguration_z_state.js"


function removeSegment(segName) {
  // Iterate over each segment to find the one with the matching name
  for (const key in RobotState.segmentsData) {
    if (RobotState.segmentsData.hasOwnProperty(key)) {
      const segment = RobotState.segmentsData[key];
      if (segment['wifi.name'] === segName) {
        // Delete the segment from the data
        delete RobotState.segmentsData[key];

        //Reorganize the remaining segments if needed
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

function updatePositionIndices() {
  const rows = document.querySelectorAll('#segment_table tbody tr');
  rows.forEach((row, index) => {
    // Get the wifi.name from the third cell (index 2) of each row
    const wifiNameCell = row.cells[2];
    const wifiName = wifiNameCell.textContent;

    // Update the position in the table
    const positionCell = row.cells[1];
    if (positionCell) {
      positionCell.textContent = index + 1; // +1 because indices are 0-based
    }

    // Update the position in the JSON data
    for (let segment in RobotState.segmentsData) {
      if (RobotState.segmentsData[segment]['wifi.name'] === wifiName) {
        RobotState.segmentsData[segment].position = index + 1;
        break; // Stop looping once the correct segment is found and updated
      }
    }
  });
}

// Shared instance will make sure that all the imports can access the same value without change in them
export { removeSegment, reorganizeSegments, callRouterApi, showToast, updatePositionIndices };
