import { redraw, removeTriangles } from './mobileController_d_pixi.js';

class ToggleButtonHandler {
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.canvas = document.getElementById("following_imageCanvas");
    this.ctx = this.canvas.getContext('2d');
    this.checkSavedState();
    this.initialSetup(); // New method to setup canvas dimensions
    this._followingState = "inactive";
    this.startPolling();
  }


  get getFollowingState() {
    return this._followingState;
  }

  initialSetup() {
    //related to canvas
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
    //related to the toggle button
    this.toggleButton.addEventListener('click', () => this.handleButtonClick());
  }

  handleButtonClick() {
    // Determine the command based on the opposite of the current button text
    let currentText = this.toggleButton.innerText;
    this.sendSwitchFollowingRequest(currentText);
  }

  sendSwitchFollowingRequest(command) {
    fetch('/switch_following', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `command=${encodeURIComponent(command)}`,
    })
      .then(response => response.json())
      .then(data => {
        this.assignFollowingState(data.received_command.following)
        // console.log(data)
        this.toggleButtonAppearance();
      })
      .catch(error => console.error("Error sending command:", error));
  }

  assignFollowingState(backendCommand) {
    switch (backendCommand) {
      case "Start Following":
        this._followingState = "active";  // The system is actively following
        break;
      case "Stop Following":
      case "ready":
        this._followingState = "inactive";  // The system is ready and not following
        break;
      case "loading":
        this._followingState = "loading";  // The system is initializing or loading
        break;
      default:
        console.log("Following: Unknown command received from the backend:", backendCommand)
    }
  }


  toggleButtonAppearance() {
    if (this._followingState == "active") {
      removeTriangles();
      this.showCanvas();
      this.toggleButton.innerText = "Stop Following";
      this.toggleButton.style.backgroundColor = "#ff6347";
    } else if (this._followingState == "inactive") {
      redraw(undefined, true, true, true);
      this.hideCanvas();
      this.toggleButton.innerText = "Start Following";
      this.toggleButton.style.backgroundColor = "#67b96a";
    } else if (this._followingState == "loading") {
      this.toggleButton.innerText = "Loading...";
      this.toggleButton.style.backgroundColor = "#ffa500";
    }
    sessionStorage.setItem("innerText", this.toggleButton.innerText);
    sessionStorage.setItem("backgroundColor", this.toggleButton.style.backgroundColor);
  }

  showCanvas() {
    this.canvas.style.display = 'block';
    if (!this.streamActive && !this.intervalId) {
      this.streamActive = true;
      this.intervalId = setInterval(() => this.refreshImage(), 150); // Start streaming
    }
  }

  hideCanvas() {
    this.canvas.style.display = 'none';
    if (this.streamActive && this.intervalId) {
      clearInterval(this.intervalId); // Stop streaming
      this.intervalId = null;
      this.streamActive = false;
    }
  }

  refreshImage() {
    if (!this.streamActive) return; // Do not proceed if streaming is not active

    const img = new Image();
    img.onload = () => {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height); // Clear previous image
      this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height); // Draw new image
    };
    img.src = '/latest_image?' + new Date().getTime(); // Include cache busting to prevent loading from cache
  }


  resizeCanvas() {
    if (this._followingState == "active") {
      removeTriangles()
      console.log("removing")
    }
    let maxWidth = window.innerWidth * 0.8; // 80% of the viewport width
    if (maxWidth > 640) maxWidth = 640; // Ensuring the width does not exceed 640 pixels
    const maxHeight = maxWidth * 3 / 4; // Maintain 4:3 ratio

    this.canvas.width = maxWidth;
    this.canvas.height = maxHeight;
    this.canvas.style.width = `${maxWidth}px`;
    this.canvas.style.height = `${maxHeight}px`;
  }

  checkSavedState() {
    if (sessionStorage.getItem("innerText") !== null) {
      this.toggleButton.innerText = sessionStorage.getItem("innerText");
      this.toggleButton.style.backgroundColor = sessionStorage.getItem("backgroundColor");
    }
    else {
    }
  }


  startPolling() {
    setInterval(() => {
      fetch('/switch_following_status', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
        .then(response => response.json())
        .then(data => {
          this.assignFollowingState(data.following_status);
          this.toggleButtonAppearance();
        })
        .catch(error => console.error("Error polling backend:", error));
    }, 1000);
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

const followingButtonHandler = new ToggleButtonHandler('following_toggle_button');

export { followingButtonHandler };
