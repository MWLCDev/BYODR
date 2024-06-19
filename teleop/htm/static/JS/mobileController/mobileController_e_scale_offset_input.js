class MotorDataInput {
  static SCALEINPUT = document.getElementById('scale_input_box_ID');
  static OFFSETINPUT = document.getElementById('offset_input_box_ID');
  static SCALEINPUT_TEXT = document.getElementById('scale-input-text');
  static OFFSETINPUT_TEXT = document.getElementById('offset-input-text');


  static hideInputElements() {
    document.getElementById('mobile-controller-top-input-container').classList.add('hidden');
  }

  static showInputElements() {
    document.getElementById('mobile-controller-top-input-container').classList.remove('hidden');

    fetch('/teleop/user/options')
      .then(response => response.json())
      .then(data => {

        // Get the current values from the backend and place them in the sliders 
        // then update the text next to the slider
        this.SCALEINPUT.value = this.SCALEINPUT_TEXT.textContent = data.vehicle["ras.driver.motor.scale"];
        this.OFFSETINPUT.value = this.OFFSETINPUT_TEXT.textContent = data.vehicle["ras.driver.steering.offset"];
      })
      .catch(error => {
        console.error('Error fetching data:', error);
      });
  }


  static sendDataToBackend() {
    // Create an array to store non-empty key-value pairs
    let scaleOffsetData = [];

    // Check and add non-empty scaleValue
    if (this.SCALEINPUT.value !== "")
      scaleOffsetData.push(["ras.driver.motor.scale", this.SCALEINPUT.value]);

    // Check and add non-empty offsetValue
    if (this.OFFSETINPUT.value !== "")
      scaleOffsetData.push(["ras.driver.steering.offset", this.OFFSETINPUT.value]);

    // Create the data object that will be sent to the backend via POST
    let data = { "vehicle": scaleOffsetData };

    // console.log('Data to send:', data);

    // Make POST request to the backend endpoint
    fetch('/teleop/user/options', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
      .then(response => {
        if (!response.ok)
          console.error('Failed to send data.');
      })
      .catch(error => {
        console.error('Error:', error);
      });
  }
}

// When the user drags the slider around, update the text next to the slider
MotorDataInput.SCALEINPUT.addEventListener('input', function () {
  // Update the text next to the slider to show the current value
  MotorDataInput.SCALEINPUT_TEXT.textContent = `${MotorDataInput.SCALEINPUT.value}`;
});

MotorDataInput.OFFSETINPUT.addEventListener('input', function () {
  // Update the text next to the slider to show the current value
  MotorDataInput.OFFSETINPUT_TEXT.textContent = `${MotorDataInput.OFFSETINPUT.value}`;
});

// When the user removes his finger from the slider, send the current value to the backend
MotorDataInput.SCALEINPUT.addEventListener('change', function () {
  // Send data to the backend
  MotorDataInput.sendDataToBackend();
});

MotorDataInput.OFFSETINPUT.addEventListener('change', function () {
  // Send data to the backend
  MotorDataInput.sendDataToBackend();
});



export { MotorDataInput };
