//Shared State variables that goes between the files/modules used

import { Dot } from "/JS/mobileController/mobileController_b_shapes.js"

class MobileControllerState {
  //The starting y coord when the triangles are relocated ()
  #initialYOffset = 0;
  #cursorFollowingDot = new Dot();
  #selectedTriangle = null;
  // Hold the current value for steering and throttle to be sent through the websocket
  #throttleSteeringJson = {};
  //stands for WebSocket
  #ws;
  #detectedTriangle = "none";
  get midScreen() {
    return window.innerHeight / 2 + this.#initialYOffset;
  }

  set initialYOffset(value) {
    this.#initialYOffset = value;
  }
  get initialYOffset() {
    return this.#initialYOffset;
  }

  set cursorFollowingDot(value) {
    this.#cursorFollowingDot = value;
  }
  get cursorFollowingDot() {
    return this.#cursorFollowingDot;
  }

  set selectedTriangle(value) {
    this.#selectedTriangle = value;
  }
  get selectedTriangle() {
    return this.#selectedTriangle;
  }

  set throttleSteeringJson(value) {
    this.#throttleSteeringJson = value;
  }
  get throttleSteeringJson() {
    return this.#throttleSteeringJson;
  }

  set websocket(value) {
    this.#ws = value;
  }
  get websocket() {
    return this.#ws;
  }

  set detectedTriangle(value) {
    if (typeof value === 'string' || value instanceof String) {
      this.#detectedTriangle = value;
    } else {
      console.error(`Value for (detectedTriangle) must be string, got ${value}`);
    }
  }
  get detectedTriangle() {
    return this.#detectedTriangle;
  }
}

const sharedState = new MobileControllerState();

// Shared instance will make sure that all the imports can access the same value without change in them
export default sharedState;