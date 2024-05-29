/**
 * Handles toggle button interactions and manages WebSocket connections for real-time data updates.
 */
class ToggleButtonHandler {
  /**
   * Constructs a ToggleButtonHandler instance.
   * @param {string} buttonId The ID of the button element to be managed.
   */
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.toggleButton.addEventListener('click', () => {
      this.handleButtonClick();
    });
    this.confidenceWS = {}; // Placeholder for WebSocket.
    this.autoReconnectInterval = 9000;
    this.initializeConfidenceWS();
  }

  /**
   * Initializes the WebSocket connection for real-time data updates and sets up event listeners.
   */
  initializeConfidenceWS() {
    let WSprotocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
    this.currentURL = `${document.location.protocol}`
    let WSurl = `${WSprotocol}${document.location.hostname}:${document.location.port}/ws/switch_confidence`;
    this.confidenceWS.websocket = new WebSocket(WSurl);

    this.confidenceWS.websocket.onopen = (event) => {
      console.log('Confidence websocket connection opened');
      this.confidenceWS.isWebSocketOpen = true;
    };

    this.confidenceWS.websocket.onmessage = (event) => {
      console.log('Confidence WS:', event.data);
      this.updateButtonState(event.data);

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

  /**
   * Checks the WebSocket's current state and attempts to reconnect if it's closed.
   */
  checkAndReconnectWebSocket() {
    if (!this.confidenceWS.websocket || this.confidenceWS.websocket.readyState === WebSocket.CLOSED) {
      this.initializeConfidenceWS();
    }
  }

  /**
   * Updates the button's appearance based on the received WebSocket message.
   * @param {string} message The message received from the WebSocket.
   */
  updateButtonState(message) {
    if (message === 'loading') {
      this.toggleButton.innerHTML = 'Loading...';
      this.toggleButton.disabled = true;
    } else if (message.endsWith('.html')) {
      // Extract the filename from the message
      const filename = message.match(/[\w-]+\.html$/)[0];

      this.toggleButton.innerHTML = 'View Results'
      this.toggleButton.disabled = false;
      this.toggleButton.onclick = () => {
        window.location.href = `${this.currentURL}/overview_confidence/${filename}`;
      };
    }
  }

  /**
   * Changes the button's appearance based on the current command.
   * @param {string} command The current text of the toggle button used to determine the new appearance.
   */
  toggleButtonAppearance(command) {
    this.toggleButton.innerText = command === "Start overview confidence" ? "Stop overview confidence" : "Start overview confidence";
    this.toggleButton.style.backgroundColor = command === "Start overview confidence" ? "#ff6347" : "#67b96a";
  }

  /**
   * Retrieves the value of a specified attribute of the toggle button.
   * @param {string} attributeName The name of the attribute to retrieve.
   * @returns {string} The value of the attribute.
   */
  getAttribute(attributeName) {
    return this.toggleButton.getAttribute(attributeName);
  }

  /**
   * Sets the value of a specified attribute of the toggle button.
   * @param {string} attributeName The name of the attribute to set.
   * @param {string} value The value to set for the attribute.
   */
  setAttribute(attributeName, value) {
    this.toggleButton.setAttribute(attributeName, value);
  }

  /**
   * Retrieves the style value of a specified property of the toggle button.
   * @param {string} property The CSS property name to retrieve.
   * @returns {string} The value of the CSS property.
   */
  getStyle(property) {
    return this.toggleButton.style[property];
  }

  /**
   * Sets the style of a specified property of the toggle button.
   * @param {string} property The CSS property name to set.
   * @param {string} value The value to set for the CSS property.
   */
  setStyle(property, value) {
    this.toggleButton.style[property] = value;
  }
}


export { ToggleButtonHandler };
