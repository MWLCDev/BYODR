/**
 * Handles toggle button interactions and manages WebSocket connections for real-time data updates.
 */
class InferenceToggleButton {
  /**
   * Constructs a InferenceToggleButton instance.
   * @param {string} buttonId The ID of the button element to be managed.
   */
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.toggleButtonContainer = document.getElementById('toggle_button_container');
    this.optionsContainer = document.getElementById('inference_options_container');
    this.hideOptionsButton = document.getElementById('hide_options');
    this.inferenceTrainingButton = document.getElementById('inference_training_toggle');
    this.InferenceAutoNavigationToggle = document.getElementById('inference_auto_navigation_toggle');
    this.confidenceWS = {}; // Placeholder for WebSocket.
    this.autoReconnectInterval = 9000;
    this.initializeConfidenceWS();
    //Means no smoothing for the other classes
    // false == working on normal mode
    // true == Inference is working on mobile controller 
    // train == Inference is on training mode
    // auto == Inference is on training mode
    this._inferenceState = "false";

    this.buttonsEventListener()
  }

  get isInference() {
  get getInferenceState() {
    return this._inferenceState;
  }

  buttonsEventListener() {
    this.toggleButton.addEventListener('click', () => this.showInferenceOptions());
    this.hideOptionsButton.addEventListener('click', () => this.hideInferenceOptions());
    this.InferenceAutoNavigationToggle.addEventListener('click', () => this.sendAutoNavigationRequest());
    this.inferenceTrainingButton.addEventListener('click', () => this.sendInferenceTrainRequest());
  }

  hideInferenceOptions() {
    this._inferenceState = "false"
    this.optionsContainer.style.display = 'none';
    this.toggleButtonContainer.style.display = 'block';
  }

  showInferenceOptions() {
    this.optionsContainer.style.display = 'block';
    this.toggleButtonContainer.style.display = 'none';
    this._inferenceState = "true"
  }

  sendInferenceTrainRequest() {
    let currentText = this.inferenceTrainingButton.innerText;
    this._inferenceState = "train"
    this.sendInferenceRequest(currentText)
    this.toggleTrainButtonAppearance(currentText)
  }
  sendAutoNavigationRequest() {
    let currentText = this.InferenceAutoNavigationToggle.innerText;
    this._inferenceState = "auto"
    this.sendInferenceRequest(currentText)
    this.toggleAutoNavigationButtonAppearance(currentText)

  }

  toggleTrainButtonAppearance(command) {
    this.inferenceTrainingButton.innerText = command === "Start Training" ? "Stop Training" : "Start Training";
    if (command == "Start Training") {
      // Switch to driver_mode.inference.dnn mode
      addKeyToSentCommand("button_y", 1)
    } else {
      // Switch to driver_mode.teleop.direct mode 
      addKeyToSentCommand("button_b", 1)
    }
  }

  toggleAutoNavigationButtonAppearance(command) {
    this.InferenceAutoNavigationToggle.innerText = command === "Start Auto-navigation" ? "Stop Auto-navigation" : "Start Auto-navigation";
  }

  /**
   * Initializes the WebSocket connection for real-time data updates and sets up event listeners.
   */
  initializeConfidenceWS() {
    let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
    this.currentURL = `${document.location.protocol}`
    let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/switch_inference`;
    this.confidenceWS.websocket = new WebSocket(WSurl);

    this.confidenceWS.websocket.onopen = (event) => {
      // console.log('Inference websocket connection opened');
      this.confidenceWS.isWebSocketOpen = true;
    };

    this.confidenceWS.websocket.onmessage = (event) => {
      console.log('Inference WS:', event.data);
      this.updateButtonState(event.data);

    };

    this.confidenceWS.websocket.onerror = (error) => {
      // console.error('WebSocket Error:', error);
    };

    this.confidenceWS.websocket.onclose = (event) => {
      console.log('Inference websocket connection closed');
      this.confidenceWS.isWebSocketOpen = false;
      // Automatically try to reconnect after a specified interval
      setTimeout(() => this.checkAndReconnectWebSocket(), this.autoReconnectInterval);
    };
  }

  /**
   * Checks the WebSocket's current state and attempts to reconnect if it's closed.
   */
  checkAndReconnectWebSocket() {
    if (!this.confidenceWS.websocket || this.confidenceWS.websocket.readyState === WebSocket.CLOSED) {
      this.initializeConfidenceWS();
    }
  }

  /**
   * Sends a command to the server via WebSocket.
   * @param {string} command The command to be sent to the server.
   */
  sendSwitchFollowingRequest(command) {
    if (this.confidenceWS.websocket && this.confidenceWS.websocket.readyState === WebSocket.OPEN) {
      this.confidenceWS.websocket.send(command);
      this.toggleButtonAppearance(command)
    } else {
      console.error("Inference websocket is not open. Command not sent. Attempting to reconnect...");
      this.checkAndReconnectWebSocket();
    }
  }
}


export { InferenceToggleButton };