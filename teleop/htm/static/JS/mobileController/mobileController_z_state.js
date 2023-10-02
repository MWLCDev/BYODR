//Shared State variables that goes between the files/modules used

import { Dot } from "/JS/mobileController/mobileController_b_shapes.js"

//The starting y coord when the triangles are relocated ()
let initialYOffset = 0;
let cursorFollowingDot = new Dot();
// null indicates no triangle is selected yet.
let selectedTriangle = null;
// Hold the current value for steering and throttle to be sent through the websocket
let throttleSteeringJson = {};
let midScreen = window.innerHeight / 2 + initialYOffset;
let detectedTriangle = "none";

function setInitialYOffset(value) {
  initialYOffset = value;
  midScreen = window.innerHeight / 2 + value;
}
function getInitialYOffset() {
  return initialYOffset;
}

function setCursorFollowingDot(value) {
  cursorFollowingDot = value;
}
function getCursorFollowingDot() {
  return cursorFollowingDot;
}

function setSelectedTriangle(value) {
  selectedTriangle = value;

}
function getSelectedTriangle() {
  return selectedTriangle;
}

function setThrottleSteeringJson(value) {
  throttleSteeringJson = value;
}
function getThrottleSteeringJson() {
  return throttleSteeringJson;
}

function setDetectedTriangle(value) {
  if (typeof value === 'string' || value instanceof String) {
    detectedTriangle = value;
  }
  else {
    console.error("Value for (detectedTriangle) must be string")
  }

}
function getDetectedTriangle() {
  return detectedTriangle;
}

function getMidScreen() {
  return midScreen;
}


export {
  setInitialYOffset, setCursorFollowingDot, setSelectedTriangle, setThrottleSteeringJson, setDetectedTriangle,
  getInitialYOffset, getCursorFollowingDot, getSelectedTriangle, getThrottleSteeringJson, getDetectedTriangle, getMidScreen,
}