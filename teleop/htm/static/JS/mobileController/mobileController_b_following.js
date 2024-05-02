class ToggleButtonHandler {
  constructor(buttonId) {
    this.toggleButton = document.getElementById(buttonId);
    this.checkSavedState();
    this.toggleButton.addEventListener('click', () => {
    this._followingState = "inactive";

  }
  get getFollowingState() {
    return this._followingState;
    console.log("Checking button state");
    if (sessionStorage.getItem("innerText") !== null){
      console.log("Button state restored")
      this.toggleButton.innerText = sessionStorage.getItem("innerText");
      this.toggleButton.style.backgroundColor = sessionStorage.getItem("backgroundColor");
    }
    else{
      console.log("No session storage found")
    }
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
        console.log("Server response:", data);
        this.toggleButtonAppearance(command);
      })
      .catch(error => console.error("Error sending command:", error));
  }

  toggleButtonAppearance(command) {
    this.toggleButton.innerText = command === "Start Following" ? "Stop Following" : "Start Following";
    this.toggleButton.style.backgroundColor = command === "Start Following" ? "#ff6347" : "#67b96a";
    sessionStorage.setItem("innerText",this.toggleButton.innerText);
    sessionStorage.setItem("backgroundColor",this.toggleButton.style.backgroundColor);
    console.log("Saved button state");
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
const followingButtonHandler = new ToggleButtonHandler('toggleButton');

// If needed to export

export { followingButtonHandler };
