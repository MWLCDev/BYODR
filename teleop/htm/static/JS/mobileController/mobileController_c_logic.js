
import { topTriangle, bottomTriangle } from "./mobileController_b_shape_triangle.js"
import CTRL_STAT from './mobileController_z_state.js';
import { redraw } from './mobileController_d_pixi.js';

function initializeWS() {
  let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
  CTRL_STAT.websocket = new WebSocket(WSurl);

  CTRL_STAT.websocket.onopen = function (event) {
    console.log('Mobile controller (WS) connection opened');
    CTRL_STAT.stateErrors = ""
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
function deltaCoordinatesFromTip(x, y) {
  // Calculate the differences in x and y coordinates to get coordinates relative to the tip
  const relativeX = x - window.innerWidth / 2;
  const relativeY = y - window.innerHeight / 2;
  SetStatistics(relativeX, relativeY);
}

function SetStatistics(x, y) {
  let shapeHeight = window.innerHeight / 4; //It is the same value as in updateDimensions()=> this.height
  CTRL_STAT.throttleSteeringJson = {
    throttle: -((y - CTRL_STAT.initialYOffset) / (window.innerHeight / 4)).toFixed(3),
    steering: Number((x / (shapeHeight / Math.sqrt(3))).toFixed(3)),
    button_b: 1,
  };
}

/**
 * Set the value for the dot on the screen, and limit the movement to be inside the triangle the user touched first
 * @param {number} x position of the touch
 * @param {number} y position of the touch
 */
function handleDotMove(touchX, touchY) {
  // the triangles are divided by a mid-point. It can be referred to as the tip (the 10 px gap)
  let minY, maxY, triangle;
  if (CTRL_STAT.selectedTriangle === 'top') {
    minY = CTRL_STAT.midScreen - topTriangle.height;
    maxY = CTRL_STAT.midScreen;
    triangle = topTriangle;
  } else if (CTRL_STAT.selectedTriangle === 'bottom') {
    minY = CTRL_STAT.midScreen;
    maxY = CTRL_STAT.midScreen + bottomTriangle.height;
    triangle = bottomTriangle;
  }
  let triangleMidX = triangle.baseWidth / 2
  let y = Math.max(minY, Math.min(touchY, maxY));
  //represents the fraction of the distance the dot is from the tip of the triangle it is inside
  const relativeY = (y - CTRL_STAT.midScreen) / triangle.height;
  //limit the movement of the ball
  const maxXDeviation = Math.abs(relativeY) * (triangleMidX);

  //The sent variable to the motors(hemisphere shape)
  let x = Math.max(Math.min(touchX, (window.innerWidth / 2) + triangleMidX), (window.innerWidth / 2) - triangleMidX);

  //X value to visually limit the movement of the ball
  let xOfDot = Math.max(Math.min(touchX, window.innerWidth / 2 + maxXDeviation), window.innerWidth / 2 - maxXDeviation);
  CTRL_STAT.cursorFollowingDot.setPosition(xOfDot, y);
  deltaCoordinatesFromTip(x, y);
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
function handleTriangleMove(y) {
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

  redraw(yOffset);
}

function sendJSONCommand() {
  intervalId = setInterval(() => {
    if (CTRL_STAT.websocket && CTRL_STAT.websocket.readyState === WebSocket.OPEN) {
      CTRL_STAT.websocket.send(JSON.stringify(CTRL_STAT.throttleSteeringJson));
    } else {
      console.error('WebSocket is not open. Unable to send data.');
    }
    // High interval to overcome if the user is controlling from the normal UI with a controller (PS4)
  }, 1);
}

export { pointInsideTriangle, deltaCoordinatesFromTip, handleDotMove, detectTriangle, handleTriangleMove, initializeWS,sendJSONCommand };
