import { addKeyToSentCommand } from "./mobileController_c_logic.js"
import { redraw, removeTriangles, changeTrianglesColor } from './mobileController_d_pixi.js';
import { topTriangle, bottomTriangle } from "./mobileController_b_shape_triangle.js"


/**
 * Handles toggle button interactions and manages WebSocket connections for real-time data updates.
 */
class InferenceToggleButton {
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.optionsContainer = document.getElementById('inference_options_container');
    this.toggleButtonContainer = document.getElementById('toggle_button_container');
    this.inferenceTrainingButton = document.getElementById('inference_training_toggle');
    this.InferenceAutoNavigationToggle = document.getElementById('inference_auto_navigation_toggle');
    this.InferenceAutoSpeedText = document.getElementById('inference_auto_speed');
    this.hideOptionsButton = document.getElementById('hide_options');
    this.logWS = {}; // Placeholder for WebSocket.
    this.logWSmessage;
    this.autoReconnectInterval = 9000;
    this.initializeLogWS();
    /*
    Means no smoothing for the other classes
     false == working on normal mode
     true == Inference is working on mobile controller 
     train == Inference is on training mode
     auto == Inference is on training mode
    */
    this._inferenceState = "false";
    this.currentAutoSpeed = 0
    this.buttonsEventListener()
  }

  get getInferenceState() {
    return this._inferenceState;
  }
  // add case that two buttons cannot be clicked together
  // it should reset all the values to zero and turn off all the buttons when exit inf mode


  buttonsEventListener() {
    this.toggleButton.addEventListener('click', () => this.showInferenceOptions());
    this.hideOptionsButton.addEventListener('click', () => this.hideInferenceOptions());
    this.inferenceTrainingButton.addEventListener('click', () => this.handleInferenceTrainClick());
    this.InferenceAutoNavigationToggle.addEventListener('click', () => this.handleAutoNavigationClick());
  }

  hideInferenceOptions() {
    redraw(undefined, undefined, true)
    this.InferenceAutoSpeedText.style.display = "none"
    this.optionsContainer.style.display = 'none';
    this.toggleButtonContainer.style.display = 'block';
    // Switch to driver_mode.teleop.direct mode 
    addKeyToSentCommand("button_b", 1)
    changeTrianglesColor()
    console.log(this._inferenceState)
    // it should turn off all the buttons to start state
    if (this._inferenceState == "auto") {
      this.handleAutoNavigationClick
      this._inferenceState = "false"
    } else if (this._inferenceState == "train") {
      this.toggleTrainButton()
      this._inferenceState = "false"
    }
    this._inferenceState = "false"
  }

  showInferenceOptions() {
    removeTriangles()
    this.optionsContainer.style.display = 'flex';
    this.toggleButtonContainer.style.display = 'none';
    this._inferenceState = "true"

  }

  handleAutoNavigationClick() {
    redraw()
    let currentText = this.InferenceAutoNavigationToggle.innerText;
    this._inferenceState = "auto"
    this.toggleAutoNavigationButton(currentText)
  }

  toggleAutoNavigationButton(command) {
    this.InferenceAutoNavigationToggle.innerText = command === "Start Auto-navigation" ? "Stop Auto-navigation" : "Start Auto-navigation";
    if (command == "Start Auto-navigation") {
      redraw()
      addKeyToSentCommand("button_y", 1)
      topTriangle.changeText("Raise Speed", 25)
      bottomTriangle.changeText("Lower Speed", 25);
      this.InferenceAutoSpeedText.style.display = "block"
      this.hideOptionsButton.innerText = "go to manual mode"
      this.inferenceTrainingButton.style.display = "none"
    } else if (command == "Stop Auto-navigation") {
      removeTriangles()
      addKeyToSentCommand("button_b", 1)
      this.InferenceAutoSpeedText.style.display = "none"
      this.inferenceTrainingButton.style.display = "flex"
      this.hideOptionsButton.innerText = "Hide Options"
    }
  }


  handleInferenceTrainClick() {
    redraw()
    let currentText = this.inferenceTrainingButton.innerText;
    this._inferenceState = "train"
    this.toggleTrainButton(currentText)
  }

  toggleTrainButton(command) {
    this.inferenceTrainingButton.innerText = command === "Start Training" ? "Stop Training" : "Start Training";
    if (command == "Start Training") {
      redraw("top", undefined, undefined)
      addKeyToSentCommand("button_y", 1)
      this.hideOptionsButton.innerText = "go to manual mode"
      this.InferenceAutoNavigationToggle.style.display = "none"
    } else {
      removeTriangles()
      addKeyToSentCommand("button_b", 1)
      this.hideOptionsButton.innerText = "Hide Options"
      this.InferenceAutoNavigationToggle.style.display = "flex"
    }

  }


  /**
   * Send message to increase to decrease the autopilot mode 
   * @param {string} touchedTriangle - name of the triangle selected
   */
  handleSpeedControl(touchedTriangle) {
    // Retrieve the current speed from the element
    const speedElement = document.getElementById("inference_auto_speed");
    // Round the received number to the nearest 0.5 for consistency
    let roundedSpeed = Math.round(this.logWSmessage.max_speed * 2) / 2;

    // Update the speed display, ensuring it always has one decimal place
    speedElement.innerHTML = `${roundedSpeed.toFixed(1)} Km/h`;

    if (touchedTriangle == "top" && roundedSpeed < 6) {
      addKeyToSentCommand("arrow_up", 1);
    } else if (touchedTriangle == "bottom" && roundedSpeed > 0) {
      addKeyToSentCommand("arrow_down", 1);
    }
  }


  initializeLogWS() {
    let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
    let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/log`;
    this.logWS.websocket = new WebSocket(WSurl);
    this.errorCount = 0; // Initialize error count

    this.logWS.websocket.onopen = (event) => {
      console.log('Log WS connection opened');
      this.logWS.isWebSocketOpen = true;
      this.errorCount = 0; // Reset error count on successful connection
      this.sendInterval = setInterval(() => {
        if (this.logWS.websocket.readyState === WebSocket.OPEN) {
          this.logWS.websocket.send('{}');
        } else {
          clearInterval(this.sendInterval); // Clear interval if not open
        }
      }, 40);
    };

    this.logWS.websocket.onmessage = (event) => {
      let jsonLogWSmessage = JSON.parse(event.data);
      this.decorate_server_message(jsonLogWSmessage)
      // console.log('Log WS:', this.logWSmessage);

      if (this.logWSmessage._is_on_autopilot
        && this.logWSmessage._has_passage == false
        && this._inferenceState != "train") {
        changeTrianglesColor(0xFF0000)
      }
    };

    this.logWS.websocket.onerror = (error) => {
      if (this.errorCount < 5) {
        console.error('WebSocket Error:', error);
        this.errorCount++;
      }
    };

    this.logWS.websocket.onclose = (event) => {
      console.log('Log WS connection closed');
      this.logWS.isWebSocketOpen = false;
      clearInterval(this.sendInterval); // Ensure interval is cleared on close
      // Automatically try to reconnect after a specified interval
      setTimeout(() => this.checkAndReconnectWebSocket(), this.autoReconnectInterval);
    };


  }

  /**
   * Add fields related to INF state to the message
   * @param {json} message Message received from log endpoint
   */
  decorate_server_message(message) {
    message._is_on_autopilot = message.ctl == 5;
    message._has_passage = message.inf_total_penalty < 1;
    if (message.geo_head == undefined) {
      message.geo_head_text = 'n/a';
    } else {
      message.geo_head_text = message.geo_head.toFixed(2);
    }
    this.logWSmessage = message
  }

  checkAndReconnectWebSocket() {
    if (!this.logWS.websocket || this.logWS.websocket.readyState === WebSocket.CLOSED) {
      this.initializeLogWS();
    }
  }

}


export { InferenceToggleButton };