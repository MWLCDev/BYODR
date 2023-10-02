import { topTriangle, bottomTriangle, Dot } from "/JS/mobileController/mobileController_b_shapes.js"

import {
  handleDotMove, detectTriangle, handleTriangleMove
} from "/JS/mobileController/mobileController_c_logic.js"

import {
  setInitialYOffset, setCursorFollowingDot, setSelectedTriangle, setThrottleSteeringJson, setDetectedTriangle,
  getInitialYOffset, getCursorFollowingDot, getSelectedTriangle, getThrottleSteeringJson, getDetectedTriangle, getMidScreen,
} from '/JS/mobileController/mobileController_z_state.js';

import { redraw, app } from "/JS/mobileController/mobileController_d_pixi.js";

let ws;
window.addEventListener('load', () => {
  let ws_protocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let ws_url = `${ws_protocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
  ws = new WebSocket(ws_url);

  ws.onopen = function (event) {
    console.log('Mobile controller (WS) connection opened');
  };

  //Check the respond from the endpoint. If the user is operator or viewer 
  // ws.onmessage = function (event) {
  //   // Handle the received data as needed
  //   // console.log('Message received:', event.data);
  // };

  ws.onerror = function (error) {
    console.log('WebSocket Error:', error);
  };

  ws.onclose = function (event) {
    console.log('Mobile controller (WS) connection closed');
  };

  console.log('Created Mobile controller (WS)');
});


window.addEventListener('resize', () => {
  app.renderer.resize(window.innerWidth, window.innerHeight);
  topTriangle.updateDimensions();
  bottomTriangle.updateDimensions();
  redraw();
});



let intervalId;
app.view.addEventListener('touchstart', (event) => {
  setInitialYOffset(event.touches[0].clientY - window.innerHeight / 2); // Calculate the initial Y offset
  detectTriangle(event.touches[0].clientX, event.touches[0].clientY);
  //if condition to make sure it will move only if the user clicks inside one of the two triangles
  if (getDetectedTriangle() !== 'none') {
    setSelectedTriangle(getDetectedTriangle()); // Set the selected triangle
    // Create the dot
    setCursorFollowingDot(new Dot());
    handleDotMove(event.touches[0].clientX, event.touches[0].clientY);
    app.stage.addChild(getCursorFollowingDot().graphics);
    handleTriangleMove(event.touches[0].clientY);

    app.view.addEventListener('touchmove', onTouchMove);
    // Arrow function to send the command through websocket 
    intervalId = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(getThrottleSteeringJson()));
      } else {
        console.error('WebSocket is not open. Unable to send data.');
      }
      // The interval is high so it overcomes if a user is controlling from the normal UI with a controller (PS4)
    }, 1);
  } else {
    console.error('Click outside the triangles. click inside one of the two triangles to start.');
  }
});

app.view.addEventListener('touchend', () => {
  //So it call the redraw function on the triangles or dot which may not have moved (due to user clicking outside the triangles)
  if (getDetectedTriangle() !== 'none') {
    redraw(); // Reset triangles to their original position

    // Remove the dot
    if (getCursorFollowingDot()) {
      getCursorFollowingDot().remove();
      setCursorFollowingDot(null);
    }
    setSelectedTriangle(null); // Reset the selected triangle
    app.view.removeEventListener('touchmove', onTouchMove); //remove the connection to save CPU
    setThrottleSteeringJson({ steering: 0, throttle: 0 }); // send the stopping signal for the motors
    clearInterval(intervalId);
  }
});

function onTouchMove(event) {
  event.preventDefault(); // Prevent scrolling while moving the triangles

  // Update the dot's position
  if (getCursorFollowingDot()) {
    handleDotMove(event.touches[0].clientX, event.touches[0].clientY);
  }
}
