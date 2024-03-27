import { addKeyToSentCommand } from "./mobileController_c_logic.js"
import { redraw, removeTriangles } from './mobileController_d_pixi.js';

/**
 * Handles toggle button interactions and manages WebSocket connections for real-time data updates.
 */
class InferenceToggleButton {
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.toggleButtonContainer = document.getElementById('toggle_button_container');
    this.optionsContainer = document.getElementById('inference_options_container');
    this.inferenceTrainingButton = document.getElementById('inference_training_toggle');
    this.InferenceAutoNavigationToggle = document.getElementById('inference_auto_navigation_toggle');
    this.hideOptionsButton = document.getElementById('hide_options');
    this.inferenceWS = {}; // Placeholder for WebSocket.
    this.autoReconnectInterval = 9000;
    this.initializeInferenceWS();
    //Means no smoothing for the other classes
    // false == working on normal mode
    // true == Inference is working on mobile controller 
    // train == Inference is on training mode
    // auto == Inference is on training mode
    this._inferenceState = "false";
    this.currentAutoSpeed = 0
    this.buttonsEventListener()
  }

  get getInferenceState() {
    return this._inferenceState;
  }
  // add case when two buttons cannot be clicked together
  // send stopping command when hiding the menu
  // it should reset all the values to zero and turn off all the buttons when exit inf mode

  handleSpeedControl(touchedTriangle) {
    if (touchedTriangle == "top") {
      addKeyToSentCommand("arrow_up", 1)
    } else if (touchedTriangle == "bottom") {
      addKeyToSentCommand("arrow_down", 1)
    }
  }

  buttonsEventListener() {
    this.toggleButton.addEventListener('click', () => this.showInferenceOptions());
    this.hideOptionsButton.addEventListener('click', () => this.hideInferenceOptions());
    this.inferenceTrainingButton.addEventListener('click', () => this.sendInferenceTrainRequest());
    this.InferenceAutoNavigationToggle.addEventListener('click', () => this.sendAutoNavigationRequest());
  }

  hideInferenceOptions() {
    redraw()
    this._inferenceState = "false"
    this.optionsContainer.style.display = 'none';
    this.toggleButtonContainer.style.display = 'block';

    // Switch to driver_mode.teleop.direct mode 
    addKeyToSentCommand("button_b", 1)
  }

  showInferenceOptions() {
    removeTriangles()
    this.optionsContainer.style.display = 'flex';
    this.toggleButtonContainer.style.display = 'none';
    this._inferenceState = "true"

  }

  sendInferenceTrainRequest() {
    redraw()
    let currentText = this.inferenceTrainingButton.innerText;
    this._inferenceState = "train"
    this.sendInferenceRequest(currentText)
    this.toggleTrainButton(currentText)
    // Switch to driver_mode.inference.dnn mode
    addKeyToSentCommand("button_y", 1)
  }

  sendAutoNavigationRequest() {
    redraw()
    let currentText = this.InferenceAutoNavigationToggle.innerText;
    this._inferenceState = "auto"
    this.sendInferenceRequest(currentText)
    this.toggleAutoNavigationButtonAppearance(currentText)
    // Switch to driver_mode.inference.dnn mode
    addKeyToSentCommand("button_y", 1)

  }

  toggleTrainButton(command) {
    this.inferenceTrainingButton.innerText = command === "Start Training" ? "Stop Training" : "Start Training";

  }

  toggleAutoNavigationButtonAppearance(command) {
    this.InferenceAutoNavigationToggle.innerText = command === "Start Auto-navigation" ? "Stop Auto-navigation" : "Start Auto-navigation";
  }

  /**
   * Initializes the WebSocket connection for real-time data updates and sets up event listeners.
   */
  initializeInferenceWS() {
    let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
    this.currentURL = `${document.location.protocol}`
    let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/switch_inference`;
    this.inferenceWS.websocket = new WebSocket(WSurl);

    this.inferenceWS.websocket.onopen = (event) => {
      // console.log('Inference websocket connection opened');
      this.inferenceWS.isWebSocketOpen = true;
    };

    this.inferenceWS.websocket.onmessage = (event) => {
      console.log('Inference WS:', event.data);
      // this.updateButtonState(event.data);

    };

    this.inferenceWS.websocket.onerror = (error) => {
      // console.error('WebSocket Error:', error);
    };

    this.inferenceWS.websocket.onclose = (event) => {
      console.log('Inference websocket connection closed');
      this.inferenceWS.isWebSocketOpen = false;
      // Automatically try to reconnect after a specified interval
      setTimeout(() => this.checkAndReconnectWebSocket(), this.autoReconnectInterval);
    };
  }

  /**
   * Checks the WebSocket's current state and attempts to reconnect if it's closed.
   */
  checkAndReconnectWebSocket() {
    if (!this.inferenceWS.websocket || this.inferenceWS.websocket.readyState === WebSocket.CLOSED) {
      this.initializeInferenceWS();
    }
  }

  /**
   * Sends a command to the server via WebSocket.
   * @param {string} command The command to be sent to the server.
   */
  sendInferenceRequest(command) {
    if (this.inferenceWS.websocket && this.inferenceWS.websocket.readyState === WebSocket.OPEN) {
      this.inferenceWS.websocket.send(command);
    } else {
      console.error("Inference websocket is not open. Command not sent. Attempting to reconnect...");
      this.checkAndReconnectWebSocket();
    }
  }
}


export { InferenceToggleButton };