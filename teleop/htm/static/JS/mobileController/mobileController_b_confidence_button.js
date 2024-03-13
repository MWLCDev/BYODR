class ToggleButtonHandler {
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.toggleButton.addEventListener('click', () => {
      this.handleButtonClick();
    });
    this.confidenceWS = {}; // Placeholder for WebSocket.
    this.autoReconnectInterval = 9000; // Time to wait before attempting to reconnect
    this.initializeConfidenceWS(); // Automatically try to open the WebSocket upon instantiation.
  }

  initializeConfidenceWS() {
    let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
    let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/switch_confidence`;
    this.confidenceWS.websocket = new WebSocket(WSurl);

    this.confidenceWS.websocket.onopen = (event) => {
      console.log('Confidence websocket connection opened');
      this.confidenceWS.isWebSocketOpen = true;
    };

    this.confidenceWS.websocket.onmessage = (event) => {
      console.log('Message from server:', event.data);
    };

    this.confidenceWS.websocket.onerror = (error) => {
      // console.error('WebSocket Error:', error);
    };

    this.confidenceWS.websocket.onclose = (event) => {
      console.log('Confidence websocket connection closed');
      this.confidenceWS.isWebSocketOpen = false;
      // Automatically try to reconnect after a specified interval
      setTimeout(() => this.checkAndReconnectWebSocket(), this.autoReconnectInterval);
    };
  }

  checkAndReconnectWebSocket() {
    // Check if WebSocket is not instantiated or if the connection is closed
    if (!this.confidenceWS.websocket || this.confidenceWS.websocket.readyState === WebSocket.CLOSED) {
      this.initializeConfidenceWS();
    }
  }

  sendSwitchFollowingRequest(command) {
    if (this.confidenceWS.websocket && this.confidenceWS.websocket.readyState === WebSocket.OPEN) {
      this.confidenceWS.websocket.send(command);
      this.toggleButtonAppearance(command)
    } else {
      console.error("Confidence websocket is not open. Command not sent. Attempting to reconnect...");
      this.checkAndReconnectWebSocket();
    }
  }

  handleButtonClick() {
    // Determine the command based on the opposite of the current button text
    let currentText = this.toggleButton.innerText;
    this.sendSwitchFollowingRequest(currentText);
  }

  /**
   * 
   * @param {string} command Current text of the toggle button 
   */
  toggleButtonAppearance(command) {
    this.toggleButton.innerText = command === "Start overview confidence" ? "Stop overview confidence" : "Start overview confidence";
    this.toggleButton.style.backgroundColor = command === "Start overview confidence" ? "#ff6347" : "#67b96a";
  }


  getAttribute(attributeName) {
    return this.toggleButton.getAttribute(attributeName);
  }

  setAttribute(attributeName, value) {
    this.toggleButton.setAttribute(attributeName, value);
  }

  getStyle(property) {
    return this.toggleButton.style[property];
  }

  setStyle(property, value) {
    this.toggleButton.style[property] = value;
  }
}

// Usage
const toggleButtonHandler = new ToggleButtonHandler('confidenceToggleButton');

// If needed to export

export { toggleButtonHandler };