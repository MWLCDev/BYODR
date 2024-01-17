import RobotState from "./robotConfiguration_z_state.js"
import { removeSegment, updatePositionIndices } from "./robotConfiguration_b_utils.js"

let tbody;
let draggedElement = null;

async function initialize() {
  tbody = await waitForTable();
}

// Method to fetch data from the API and display it
async function fetchSegmentDataAndDisplay() {
  try {
    const response = await fetch('/teleop/robot/options');
    const jsonData = await response.json();
    RobotState.robotConfigData = jsonData;
    RobotState.segmentsData = jsonData;
    // console.log(RobotState.segmentsData)
    updateSegmentsTable();
  } catch (error) {
    console.error('There has been a problem with your fetch operation:', error);
  }
}

function waitForTable() {
  return new Promise((resolve) => {
    const checkExist = setInterval(() => {
      const tbody = document.querySelector('#container_segment_table table tbody');
      if (tbody) {
        clearInterval(checkExist);
        resolve(tbody);
      }
    }, 100); // Check every 100ms
  });
}

function updateSegmentsTable() {
  tbody.innerHTML = '';
  for (const segment in RobotState.segmentsData) {
    if (RobotState.segmentsData.hasOwnProperty(segment) && segment.startsWith('segment_')) {
      const row = RobotState.segmentsData[segment];
      const tr = document.createElement('tr');

      const isMainSegment = row['host'] === 'True';

      tr.innerHTML = `
        <td></td>
        <td></td>
        <td>${row['vin.number']}</td>
        <td>${row['mac.address']}</td>
        <td>${row['wifi.name']}</td>
        <td><input type="radio" name="mainSegment" ${isMainSegment ? 'checked' : ''}></td>
        ${isMainSegment ? '' : '<td><button type="button" data-wifiname="${row["wifi.name"]}">Remove</button></td>'}
      `;
      tbody.appendChild(tr);
      // Find the newly created button and attach the deleting click event listener
      $('#application-content-container').on('click', '#segment_table tbody button[data-wifiname]', (e) => {
        const wifiName = $(e.currentTarget).data('wifiname');
        removeSegment(wifiName);
        updateSegmentsTable();
      });
    }
  }
  addNewRow()
}

function addNewRow() {
  // After adding all rows, append an extra row for input
  const inputRow = document.createElement('tr');
  inputRow.innerHTML = `
     <td></td>
     <td></td>
     <td><input type="text" placeholder="VIN Number"></td>
     <td><input type="text" placeholder="IP"></td>
     <td><input type="text" placeholder="WiFi Name"></td>
     <td><input type="radio" name="mainSegment"></td>
     <td><button type="button" onclick="addNewSegment()">Add</button></td>
   `;
  tbody.appendChild(inputRow);
  updatePositionIndices();
}

function enableDragAndDrop() {
  updatePositionIndices();
  // Adding touch and mouse events to the tbody
  $('#application-content-container').on('touchstart', '#segment_table tbody', (e) => handleDragStart(e));
  $('#application-content-container').on('touchmove', '#segment_table tbody', (e) => handleDragMove(e.touches[0]));
  $('#application-content-container').on('touchend', '#segment_table tbody', () => handleDragEnd());
  $('#application-content-container').on('mousedown', '#segment_table tbody', (e) => handleDragStart(e));
  $('#application-content-container').on('mousemove', '#segment_table tbody', (e) => handleDragMove(e));
  $('#application-content-container').on('mouseup', '#segment_table tbody', () => handleDragEnd());

}

function handleDragStart(event) {
  if (event.target === event.target.closest('tr').firstElementChild) {
    const row = event.target.closest('tr');
    if (row && row.parentNode === tbody) {
      draggedElement = row;
      draggedElement.classList.add('floating');
    }
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
    // Ensure that draggedElement is a valid DOM element
    if (draggedElement instanceof HTMLElement) {
      draggedElement.style.transition = 'transform 0.2s, box-shadow 0.2s';
      draggedElement.classList.remove('floating');
      setTimeout(() => {
        if (draggedElement instanceof HTMLElement) {
          draggedElement.style.transition = '';
        }
      }, 200);
    }

    draggedElement = null;

    // Call updatePositionIndices after a row has been repositioned
    updatePositionIndices();
  }
}

function swapRows(row1, row2) {
  const parentNode = row1.parentNode;
  const nextSibling = row1.nextElementSibling === row2 ? row1 : row1.nextElementSibling;
  parentNode.insertBefore(row2, nextSibling);
}

document.addEventListener('DOMContentLoaded', initialize);


export { enableDragAndDrop, fetchSegmentDataAndDisplay, updateSegmentsTable, addNewRow }