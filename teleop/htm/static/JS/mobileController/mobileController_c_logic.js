
import { cursorFollowingDot } from "./mobileController_b_shape_dot.js";
import { bottomTriangle, topTriangle } from "./mobileController_b_shape_triangle.js";

import { drawBottomTriangle_TopRectangle, drawTopTriangle_BottomRectangle, redraw } from './mobileController_d_pixi.js';
import CTRL_STAT from './mobileController_z_state.js';

function initializeWS() {
  let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
  CTRL_STAT.websocket = new WebSocket(WSurl);

  CTRL_STAT.websocket.onopen = function (event) {
    console.log('Mobile controller (WS) connection opened');
    addKeyToSentCommand("button_b", 1)
    CTRL_STAT.stateErrors = ""
    CTRL_STAT.isWebSocketOpen = true;
  };

  // Check the respond from the endpoint. If the user is operator or viewer 
  // if it is a viewer, then refresh
  CTRL_STAT.websocket.onmessage = function (event) {
    let parsedData = JSON.parse(event.data); // The received data is in string, so I need to convert to JSON 
    if (parsedData["control"] == "operator") {
      //Place holder until implementation with multi segment is over
    } else if (parsedData["control"] == "viewer") {
      CTRL_STAT.stateErrors = "controlError"
      redraw(undefined, true, true, false);
    }
  };

  CTRL_STAT.websocket.onerror = function (error) {
    console.log('WebSocket Error:', error);
  };

  CTRL_STAT.websocket.onclose = function (event) {
    console.log('Mobile controller (WS) connection closed');
    CTRL_STAT.stateErrors = "connectionError"
    redraw(undefined, true, true, false);
    CTRL_STAT.isWebSocketOpen = false; // Reset the flag when WebSocket is closed
  };
}

/**
 * Check if a point is inside a triangle using barycentric
 * @param {number} px Point's x-coord
 * @param {number} py Point's Y-coord
 * @param {number} ax Triangle's 1st edge x-coord
 * @param {number} ay Triangle's 1st edge y-coord
 * @param {number} bx Triangle's 2nd edge x-coord
 * @param {number} by Triangle's 2nd edge y-coord
 * @param {number} cx Triangle's 3rd edge x-coord
 * @param {number} cy Triangle's 3rd edge y-coord
 * @returns 
 */
function pointInsideTriangle(px, py, ax, ay, bx, by, cx, cy) {
  // Compute vectors
  const v0 = [cx - ax, cy - ay];
  const v1 = [bx - ax, by - ay];
  const v2 = [px - ax, py - ay];

  // Compute dot products
  const dot00 = v0[0] * v0[0] + v0[1] * v0[1];
  const dot01 = v0[0] * v1[0] + v0[1] * v1[1];
  const dot02 = v0[0] * v2[0] + v0[1] * v2[1];
  const dot11 = v1[0] * v1[0] + v1[1] * v1[1];
  const dot12 = v1[0] * v2[0] + v1[1] * v2[1];

  // Compute barycentric coordinates
  const invDenom = 1 / (dot00 * dot11 - dot01 * dot01);
  const u = (dot11 * dot02 - dot01 * dot12) * invDenom;
  const v = (dot00 * dot12 - dot01 * dot02) * invDenom;

  // Check if the point is inside the triangle
  return u >= 0 && v >= 0 && u + v < 1;
}

/**
 * Calculate and set differences in y coordinate relative to the screen's center,
 * effectively determining the position and movement of the control dot relative to the triangle tip.
 * @param {number} user_touch_X - X position of the user's touch input.
 */
function deltaCoordinatesFromTip(user_touch_X) {
  let relativeX = user_touch_X - window.innerWidth / 2;
  return relativeX
}


function SetStatistics(user_touch_X, user_touch_Y, y, getInferenceState) {
  let shapeHeight = window.innerHeight / 4; //It is the same value as in updateDimensions()=> this.height
  const isTopTriangle = CTRL_STAT.selectedTriangle === 'top'; // Checking if the top triangle is in use
  const isTouchBelowCenter = user_touch_Y >= window.innerHeight / 2; // Checking if the finger of the user is below the center line of the screen


  // Stopping the robot urgently depending on where the finger of the user is. We stop in these cases:
  // top triangle in use AND finger below the center
  // OR
  // bottom triangle in use AND finger above the center
  // In this case will immediately stop
  if (isTopTriangle === isTouchBelowCenter)
    // Removing the throttle key in the JSON, since the robot will only forward commands if they have the 'throttle' key inside
    CTRL_STAT.throttleSteeringJson = {};

  // In any other case, we produce commands normally
  else
    CTRL_STAT.throttleSteeringJson = {
      throttle: -(y).toFixed(3),
      steering: Number((user_touch_X / (shapeHeight / Math.sqrt(3))).toFixed(3)),
      mobileInferenceState: getInferenceState,
    };
}

// Save dead zone width to local storage
function saveDeadZoneWidth(value) {
  localStorage.setItem('deadZoneWidth', value);
}

// Retrieve dead zone width from local storage
function getSavedDeadZoneWidth() {
  // If there's a saved value in local storage, use it; otherwise default to 0.1
  return localStorage.getItem('deadZoneWidth') || '0.1';
}

/**
 * Handles the movement of the dot within specified triangle boundaries.
 * @param {number} touchX - X position of the touch.
 * @param {number} touchY - Y position of the touch.
 * @param {*} getInferenceState - Function to get the current inference state.
 */
function handleDotMove(touchX, touchY, getInferenceState) {
  // Determine the triangle and its vertical boundaries based on the selection.
  const isTopTriangle = CTRL_STAT.selectedTriangle === 'top';
  const triangle = isTopTriangle ? topTriangle : bottomTriangle;
  const midScreen = window.innerHeight / 2;

  // Calculate minY and maxY based on the mode.
  let minY, maxY;
  if (getInferenceState === "auto") {
    minY = isTopTriangle ? midScreen - triangle.height : midScreen;
    maxY = isTopTriangle ? midScreen : midScreen + triangle.height;
  } else {
    minY = isTopTriangle ? CTRL_STAT.midScreen - triangle.height : CTRL_STAT.midScreen;
    maxY = isTopTriangle ? CTRL_STAT.midScreen : CTRL_STAT.midScreen + triangle.height;
  }

  // Constrain the Y position within the triangle's boundaries.
  let y = Math.max(minY, Math.min(touchY, maxY));

  // Calculate the relative Y position within the triangle.
  // This is initialized here to ensure it has a value in all code paths.
  let relativeY = (y - (getInferenceState === "auto" ? midScreen : CTRL_STAT.midScreen)) / triangle.height;

  let deadZoneSlider = document.getElementById('deadZoneWidth');
  let savedDeadZoneWidth = getSavedDeadZoneWidth();
  deadZoneSlider.value = savedDeadZoneWidth; // Set the slider to the saved value
  let deadZoneWidth = window.innerWidth * parseFloat(savedDeadZoneWidth);

  let deadZoneMinX = (window.innerWidth / 2) - (deadZoneWidth / 2);
  let deadZoneMaxX = (window.innerWidth / 2) + (deadZoneWidth / 2);
  let inDeadZone = touchX >= deadZoneMinX && touchX <= deadZoneMaxX;

  // Modify the logic to handle the X position considering the dead zone
  let xOfDot;

  if (inDeadZone) {
    xOfDot = window.innerWidth / 2;
    relativeY = (y - CTRL_STAT.midScreen) / triangle.height; // Default value when in dead zone, adjust as necessary
  } else {
    let maxXDeviation = Math.abs(relativeY) * (triangle.baseWidth / 2);
    xOfDot = Math.max(Math.min(touchX, window.innerWidth / 2 + maxXDeviation), window.innerWidth / 2 - maxXDeviation);
  }

  // Update the dot's position.
  cursorFollowingDot.setPosition(xOfDot, y);
  if (inDeadZone) {
    SetStatistics(0, y, relativeY, getInferenceState);
  } else if (getInferenceState !== "auto") {
    let relative_x = deltaCoordinatesFromTip(touchX);
    SetStatistics(relative_x, touchY, relativeY, getInferenceState);
  }
}

/**
 * Second way to limit the user's interactions, to be only inside the two triangles (first one is the if condition in handleTriangleMove() to limit the borders of the triangles)
 * @param {number} x the x-value for the position of touch
 * @param {number} y The y-value for the position of touch
 * @returns If the touch was in any of the two triangles, or even out
 */
function detectTriangle(x, y) {
  //Lots of spread syntax/ destructuring for the values of vertices in triangles
  if (pointInsideTriangle(x, y, ...topTriangle.vertices[0], ...topTriangle.vertices[1], ...topTriangle.vertices[2])) {
    CTRL_STAT.detectedTriangle = 'top';
  } else if (pointInsideTriangle(x, y, ...bottomTriangle.vertices[0], ...bottomTriangle.vertices[1], ...bottomTriangle.vertices[2])) {
    CTRL_STAT.detectedTriangle = 'bottom';
  } else {
    CTRL_STAT.detectedTriangle = 'none';
  }
  CTRL_STAT.selectedTriangle = CTRL_STAT.detectedTriangle;
}

/**
 * limit the triangles not to go outside the borders of the screen
 * @param {number} y Y-coord where the user's input is 
 */
function handleTriangleMove(y, inferenceToggleButton) {
  const midScreen = window.innerHeight / 2;
  let yOffset = y - midScreen;

  const maxOffset = midScreen + topTriangle.height; // Maximum offset for the top triangle
  const minOffset = midScreen + bottomTriangle.height; // Minimum offset for the bottom triangle

  // Clamping the yOffset value to stop the triangles from crossing the screen's border
  if (yOffset > 0) {
    yOffset = Math.min(yOffset, minOffset - midScreen);
  } else {
    yOffset = Math.max(yOffset, -(maxOffset - midScreen));
  }

  let INFState = inferenceToggleButton.getInferenceState
  if (INFState == "auto") {
    inferenceToggleButton.handleSpeedControl(CTRL_STAT.selectedTriangle)
    //you should be able to move it while on training mode
  } else if (INFState == "train") {
    redraw(yOffset, true, false, true);
  } else if (CTRL_STAT.detectedTriangle === 'top' && INFState != "true") {
    document.getElementById('toggle_button_container').style.display = 'none';
    drawTopTriangle_BottomRectangle(yOffset);
  }
  else if (CTRL_STAT.detectedTriangle === 'bottom' && INFState != "true") {
    document.getElementById('toggle_button_container').style.display = 'none';
    drawBottomTriangle_TopRectangle(yOffset);
  }


  else if (CTRL_STAT.detectedTriangle === 'top') {
    document.getElementById('toggle_button_container').style.display = 'none';
    drawTopTriangle_BottomRectangle(yOffset);
  }
  else if (CTRL_STAT.detectedTriangle === 'bottom') {
    document.getElementById('toggle_button_container').style.display = 'none';
    drawBottomTriangle_TopRectangle(yOffset);
  }
}

/**
 * Function to add a temporary key-value pair to the sent command through mobile controller socket
 * @param {string} key 
 * @param {string} value 
 */
function addKeyToSentCommand(key, value) {
  CTRL_STAT.throttleSteeringJson[key + "_temp"] = value;

}

function sendJSONCommand() {
  if (CTRL_STAT.websocket && CTRL_STAT.websocket.readyState === WebSocket.OPEN) {
    // Create a copy of the data to send, removing '_temp' from temporary keys
    const dataToSend = {};
    for (const key in CTRL_STAT.throttleSteeringJson) {
      if (key.endsWith('_temp')) {
        const originalKey = key.slice(0, -5); // Remove last 5 characters ('_temp')
        dataToSend[originalKey] = CTRL_STAT.throttleSteeringJson[key];
      } else {
        dataToSend[key] = CTRL_STAT.throttleSteeringJson[key];
      }
    }

    CTRL_STAT.websocket.send(JSON.stringify(dataToSend));
    CTRL_STAT.isWebSocketOpen = true;

    Object.keys(CTRL_STAT.throttleSteeringJson).forEach(key => {
      if (key.endsWith('_temp')) {
        delete CTRL_STAT.throttleSteeringJson[key];
      }
    });

  } else {
    if (CTRL_STAT.isWebSocketOpen) {
      console.error('WebSocket is not open. Unable to send data.');
      CTRL_STAT.isWebSocketOpen = false;
    }
  }

  setTimeout(sendJSONCommand, 100);
}

export { addKeyToSentCommand, deltaCoordinatesFromTip, detectTriangle, getSavedDeadZoneWidth, handleDotMove, handleTriangleMove, initializeWS, pointInsideTriangle, saveDeadZoneWidth, sendJSONCommand };

