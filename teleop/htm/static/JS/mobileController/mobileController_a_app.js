import { InferenceToggleButton } from "./mobileController_b_shape_Inference.js"
import { bottomTriangle, topTriangle } from "./mobileController_b_shape_triangle.js"
import { detectTriangle, getSavedDeadZoneWidth, handleDotMove, handleTriangleMove, initializeWS, saveDeadZoneWidth, sendJSONCommand } from "./mobileController_c_logic.js"
import { cursorFollowingDot } from "./mobileController_b_shape_dot.js";

import { ToggleButtonHandler } from "./mobileController_b_shape_confidence.js"

import { app, changeTrianglesColor, redraw } from "./mobileController_d_pixi.js"
import CTRL_STAT from './mobileController_z_state.js'; // Stands for control state

// Initialize sending commands only once, instead of calling it each time we touch the triangles
sendJSONCommand();
let intervalId;
let inferenceToggleButton

window.addEventListener('load', () => {
  initializeWS()
  inferenceToggleButton = new InferenceToggleButton("inference_toggle_button")
  changeTrianglesColor(0x000000)
  new ToggleButtonHandler('confidenceToggleButton')
  let deadZoneSlider = document.getElementById('deadZoneWidth');
  deadZoneSlider.value = getSavedDeadZoneWidth(); // Initialize slider with saved value
});

// Dead zone width slider input event listener
document.getElementById('deadZoneWidth').addEventListener('input', function () {
  let value = this.value;
  // Save the new dead zone width to local storage after handling the dot move
  saveDeadZoneWidth(value);
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
        document.getElementById("mobile-controller-top-input-container").style.display = "none";
        document.getElementById("mobile-controller-bottom-input-container").style.display = "none";
        startOperating(event)
        app.view.addEventListener('touchmove', onTouchMove);
        break;
    }
  } else {
    console.error('Clicked outside the triangles. click inside one of the two triangles to start.');
  }
});


function startOperating(event) {
  cursorFollowingDot.show()
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
  handleDotMove(event.touches[0].clientX, event.touches[0].clientY, inferenceToggleButton.getInferenceState);
}


app.view.addEventListener('touchend', () => {
  //So it call the redraw function on the triangles or dot which may not have moved (due to user clicking outside the triangles)
  if (CTRL_STAT.detectedTriangle !== 'none') {
    if (inferenceToggleButton.getInferenceState != "true") {
      document.getElementById("mobile-controller-top-input-container").style.display = "flex";
      document.getElementById("mobile-controller-bottom-input-container").style.display = "flex";

      redraw(); // Reset triangles to their original position

      CTRL_STAT.selectedTriangle = null; // Reset the selected triangle
      app.view.removeEventListener('touchmove', onTouchMove); //remove the connection to save CPU
      CTRL_STAT.throttleSteeringJson = { steering: 0, throttle: 0 }; // send the stopping signal for the motors
      // so it doesn't show the div when in inference mode
      if (inferenceToggleButton.getInferenceState == "false") {
        document.getElementById('toggle_button_container').style.display = 'flex';
      }
      if (inferenceToggleButton.getInferenceState == "train") {
        document.getElementById('inference_options_container').style.display = 'flex';
        redraw(undefined, true, true, true)
      }
      cursorFollowingDot.hide()
      clearTimeout(intervalId);
    }
  }
});
