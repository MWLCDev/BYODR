import { topTriangle, bottomTriangle } from "./mobileController_b_shape_triangle.js"
import { Dot } from "./mobileController_b_shape_dot.js"
import { handleDotMove, detectTriangle, handleTriangleMove, initializeWS, sendJSONCommand }
  from "./mobileController_c_logic.js"

import { ToggleButtonHandler } from "./mobileController_b_confidence_button.js"

import CTRL_STAT from './mobileController_z_state.js'; // Stands for control state
import { redraw, app } from "./mobileController_d_pixi.js";

// Initialize sending commands only once, instead of calling it each time we touch the triangles
// The function would keep stacking, sending commands more often than 10 times a second
// Now we call it once, and we just change the commands that are being sent
// At first we send a default value
CTRL_STAT.throttleSteeringJson = { steering: 0, throttle: 0 };
sendJSONCommand()


window.addEventListener('load', () => {
  initializeWS()
  new ToggleButtonHandler('confidenceToggleButton')
});

window.addEventListener('resize', () => {
  app.renderer.resize(window.innerWidth, window.innerHeight);
  topTriangle.updateDimensions();
  bottomTriangle.updateDimensions();
  redraw();
});

let intervalId;
app.view.addEventListener('touchstart', (event) => {
  CTRL_STAT.initialYOffset = event.touches[0].clientY - window.innerHeight / 2; // Calculate the initial Y offset
  detectTriangle(event.touches[0].clientX, event.touches[0].clientY);
  //if condition to make sure it will move only if the user clicks inside one of the two triangles
  if (CTRL_STAT.detectedTriangle !== 'none') {
    switch (CTRL_STAT.stateErrors) {
      case "controlError":
        console.error("Another user has connected. Refresh the page to take control back");
        break;
      case "connectionError":
        console.error("Connection lost with the robot. Please reconnect");
        break;
      default:
        startOperating(event)
        app.view.addEventListener('touchmove', onTouchMove);
        // Arrow function to send the command through websocket 
        break;
    }
  } else {
    console.error('Clicked outside the triangles. click inside one of the two triangles to start.');
  }
});

function startOperating(event) {
  CTRL_STAT.selectedTriangle = CTRL_STAT.detectedTriangle;
  CTRL_STAT.cursorFollowingDot = new Dot();
  handleDotMove(event.touches[0].clientX, event.touches[0].clientY);
  app.stage.addChild(CTRL_STAT.cursorFollowingDot.graphics);
  handleTriangleMove(event.touches[0].clientY);
}


app.view.addEventListener('touchend', () => {
  //So it call the redraw function on the triangles or dot which may not have moved (due to user clicking outside the triangles)
  if (CTRL_STAT.detectedTriangle !== 'none') {
    redraw(); // Reset triangles to their original position

    // Remove the dot
    if (CTRL_STAT.cursorFollowingDot) {
      CTRL_STAT.cursorFollowingDot.remove();
      CTRL_STAT.cursorFollowingDot = null;
    }
    CTRL_STAT.selectedTriangle = null; // Reset the selected triangle
    app.view.removeEventListener('touchmove', onTouchMove); //remove the connection to save CPU
    CTRL_STAT.throttleSteeringJson = { steering: 0, throttle: 0 }; // send the stopping signal for the motors
    clearTimeout(intervalId);
  }
});

function onTouchMove(event) {
  event.preventDefault(); // Prevent scrolling while moving the triangles

  // Update the dot's position
  if (CTRL_STAT.cursorFollowingDot) {
    handleDotMove(event.touches[0].clientX, event.touches[0].clientY);
  }
}
