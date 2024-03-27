import { topTriangle, bottomTriangle } from "./mobileController_b_shape_triangle.js"
import { Dot } from "./mobileController_b_shape_dot.js"
import { handleDotMove, detectTriangle, handleTriangleMove, initializeWS, sendJSONCommand }
  from "./mobileController_c_logic.js"
import { InferenceToggleButton } from "./mobileController_b_shape_Inference.js"

import CTRL_STAT from './mobileController_z_state.js'; // Stands for control state
import { redraw, app } from "./mobileController_d_pixi.js";

// Initialize sending commands only once, instead of calling it each time we touch the triangles
sendJSONCommand()
let intervalId;
let inferenceToggleButton

window.addEventListener('load', () => {
  initializeWS()
  inferenceToggleButton = new InferenceToggleButton("inference_toggle_button")
});

window.addEventListener('resize', () => {
  app.renderer.resize(window.innerWidth, window.innerHeight);
  topTriangle.updateDimensions();
  bottomTriangle.updateDimensions();
  redraw();
});

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
  if (app.stage.children.includes(CTRL_STAT.cursorFollowingDot)) {
    CTRL_STAT.cursorFollowingDot.show()
  }
  else {
    CTRL_STAT.cursorFollowingDot = new Dot();
  }
  handleDotMove(event.touches[0].clientX, event.touches[0].clientY, inferenceToggleButton.getInferenceState);
  handleTriangleMove(event.touches[0].clientY, inferenceToggleButton);
  if (inferenceToggleButton.getInferenceState == "train") {
    document.getElementById('inference_options_container').style.display = 'none';
  }
}

function onTouchMove(event) {
  event.preventDefault(); // Prevent scrolling while moving the triangles
  if (inferenceToggleButton.getInferenceState == "train") {
    document.getElementById('inference_options_container').style.display = 'none';
  }
  // Update the dot's position
  if (CTRL_STAT.cursorFollowingDot) {
    handleDotMove(event.touches[0].clientX, event.touches[0].clientY, inferenceToggleButton.getInferenceState);
  }
}


app.view.addEventListener('touchend', () => {

  //So it call the redraw function on the triangles or dot which may not have moved (due to user clicking outside the triangles)
  if (CTRL_STAT.detectedTriangle !== 'none') {
    redraw(); // Reset triangles to their original position
    CTRL_STAT.cursorFollowingDot.hide()
    CTRL_STAT.selectedTriangle = null; // Reset the selected triangle
    app.view.removeEventListener('touchmove', onTouchMove); //remove the connection to save CPU
    CTRL_STAT.throttleSteeringJson = { steering: 0, throttle: 0 }; // send the stopping signal for the motors
    // so it doesn't show the div when in inference mode
    if (inferenceToggleButton.getInferenceState == "false") {
      document.getElementById('toggle_button_container').style.display = 'block';
    }
    if (inferenceToggleButton.getInferenceState == "train") {
      document.getElementById('inference_options_container').style.display = 'flex';
    }

    clearTimeout(intervalId);
  }
});

