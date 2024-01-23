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
    data: segment.data
  }));
}


/**
 * Removes all segments from RobotState.segmentsData that start with "segment_".
 */
function removeAllSegments() {
  Object.keys(RobotState.segmentsData)
    .filter(key => key.startsWith('segment_'))
    .forEach(segKey => removeSegment(RobotState.segmentsData[segKey]['wifi.name']));
}

/**
 * Adds the given segments back into RobotState.segmentsData.
 * @param {Array} segments - The array of segments to be re-added.
 */
function reAddSegments(segments) {
  segments.forEach(segment => {
    RobotState.segmentsData[segment.key] = segment.data;
  });
}

// The function should read the data from the table and sort them in the json according to the way they are in table
export { removeSegment, reorganizeSegments, callRouterApi, showToast, updatePositionIndices };
