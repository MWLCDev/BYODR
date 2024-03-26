
import { topTriangle, bottomTriangle } from "./mobileController_b_shape_triangle.js"
import CTRL_STAT from './mobileController_z_state.js';
import { redraw, drawTopTriangle_BottomRectangle, drawBottomTriangle_TopRectangle } from './mobileController_d_pixi.js';

function initializeWS() {
  let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
  // let WSurl = `${WSprotocol}192.168.2.100:${document.location.port}/ws/send_mobile_controller_commands`;
  let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
  CTRL_STAT.websocket = new WebSocket(WSurl);

  CTRL_STAT.websocket.onopen = function (event) {
    console.log('Mobile controller (WS) connection opened');
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
    }
  };

  CTRL_STAT.websocket.onerror = function (error) {
    console.log('WebSocket Error:', error);
  };

  CTRL_STAT.websocket.onclose = function (event) {
    console.log('Mobile controller (WS) connection closed');
    CTRL_STAT.stateErrors = "connectionError"
    CTRL_STAT.isWebSocketOpen = false; // Reset the flag when WebSocket is closed
  };
  console.log('Created Mobile controller (WS)');
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
 * Prints x,y and distance from the tip of the triangle to the current place of the ball.
 * @param {number} x current position of the ball (same as touch)
 * @param {*} y current position for the ball (same as touch)
 */
function deltaCoordinatesFromTip(x, y, user_touch_Y, getInferenceState) {
  // Calculate the differences in x and y coordinates to get coordinates relative to the tip
  const relativeX = x - window.innerWidth / 2;
  const relativeY = y - window.innerHeight / 2;
  SetStatistics(relativeX, relativeY, user_touch_Y, getInferenceState);
}

function SetStatistics(x, y, user_touch_Y, getInferenceState) {
  let shapeHeight = window.innerHeight / 4; //It is the same value as in updateDimensions()=> this.height
  const isTopTriangle = CTRL_STAT.selectedTriangle === 'top'; // Checking if the top triangle is in use
  const isTouchBelowCenter = user_touch_Y >= window.innerHeight / 2; // Checking if the finger of the user is below the center line of the screen

  // Stopping the robot urgently depending on where the finger of the user is. We stop in these cases:
  // top triangle in use AND finger below the center
  // OR
  // bottom triangle in use AND finger above the center
  // This is the definition of an XNOR gate, and the equivalent in JS is the '===' operator
  // In this case, the robot will not decelerate slowly, it will immediately stop
  if (isTopTriangle === isTouchBelowCenter)
    // Removing the throttle key in the JSON, since the robot will only forward commands if they have the 'throttle' key inside
    CTRL_STAT.throttleSteeringJson = {};

  // In any other case, we produce commands normally
  else
    CTRL_STAT.throttleSteeringJson = {
      throttle: -((y - CTRL_STAT.initialYOffset) / (window.innerHeight / 4)).toFixed(3),
      steering: Number((x / (shapeHeight / Math.sqrt(3))).toFixed(3)),
      mobileInferenceState: getInferenceState,
    };
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
  const minY = isTopTriangle ? CTRL_STAT.midScreen - triangle.height : CTRL_STAT.midScreen;
  const maxY = isTopTriangle ? CTRL_STAT.midScreen : CTRL_STAT.midScreen + triangle.height;

  // Constrain the Y position within the triangle's boundaries.
  let y = Math.max(minY, Math.min(touchY, maxY));

  // Calculate the relative Y position within the triangle to determine horizontal movement limit.
  let relativeY = (y - CTRL_STAT.midScreen) / triangle.height;
  let maxXDeviation = Math.abs(relativeY) * (triangle.baseWidth / 2);

  // Constrain the X position within the calculated horizontal movement limit.
  let xOfDot = Math.max(Math.min(touchX, window.innerWidth / 2 + maxXDeviation), window.innerWidth / 2 - maxXDeviation);

  // Log for debugging.
  console.log(minY, y, relativeY, maxXDeviation, xOfDot)

  // Update the dot's position and calculate coordinates relative to the tip.
  CTRL_STAT.cursorFollowingDot.setPosition(xOfDot, y);
  deltaCoordinatesFromTip(touchX, y, touchY, getInferenceState);
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
}

/**
 * limit the triangles not to go outside the borders of the screen
 * @param {number} y Y-coord where the user's input is 
 */
function handleTriangleMove(y, getInferenceState) {
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
  if (isInference) {
  if (getInferenceState == "true") {
    redraw(yOffset);
  } else {
    if (CTRL_STAT.detectedTriangle === 'top')
      drawTopTriangle_BottomRectangle(yOffset);
    else
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

export { pointInsideTriangle, deltaCoordinatesFromTip, handleDotMove, detectTriangle, handleTriangleMove, initializeWS, sendJSONCommand, addKeyToSentCommand };
