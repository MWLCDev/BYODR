//Shared State variables that goes between the files/modules used

import { topTriangle} from "./mobileController_b_shape_triangle.js"

class MobileControllerState {
  //The starting y coord when the triangles are relocated ()
  #initialYOffset = 0;
  #selectedTriangle = null;
  // Hold the current value for steering and throttle to be sent through the websocket
  // At first we send a default value
  #throttleSteeringJson = { steering: 0, throttle: 0};
  //stands for WebSocket
  #ws;
  #stateErrors;
  #isWebSocketOpen

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

  set stateErrors(value) {
    if (this.#stateErrors != value) {
      this.#stateErrors = value;
      topTriangle.changeText(value)
    }
  }
  get stateErrors() {
    return this.#stateErrors;
  }

  set websocket(value) {
    this.#ws = value;
  }
  get websocket() {
    return this.#ws;
  }

  set isWebSocketOpen(value) {
    this.#isWebSocketOpen = value;
  }
  get isWebSocketOpen() {
    return this.#isWebSocketOpen;
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