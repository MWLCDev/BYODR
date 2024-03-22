class MotorDataInput{
  static SCALEINPUT = document.getElementById('scale_input_box_ID');
  static OFFSETINPUT = document.getElementById('offset_input_box_ID');
  static CONFIRMBUTTON = document.getElementById('scale_offset_confirm_button_ID');
  static CONFIRM_CHANGE_TEXT = document.querySelector('.scale-offset-confirm-text');

  static hideInputElements() {
    document.querySelector('.mobile-controller-motor-settings-container').classList.add('hidden');
  }

  static showInputElements() {
    document.querySelector('.mobile-controller-motor-settings-container').classList.remove('hidden');

    fetch('/teleop/user/options')
      .then(response => response.json())
      .then(data => {
        this.SCALEINPUT.value = data.vehicle["ras.driver.motor.scale"];
        this.OFFSETINPUT.value = data.vehicle["ras.driver.steering.offset"];
        this.updateConfirmButton();
      })
      .catch(error => {
        console.error('Error fetching data:', error);
      });
  }

  static isValidScaleInput(value) {
    const min = 0.0;
    const max = 10.0;
    const scale_regex = /^([1-9]\d?(\.\d\d?)?)?$/;

    return (scale_regex.test(value) && parseFloat(value) >= min && parseFloat(value) <= max);
  }

  static isValidOffsetInput(value) {
    const min = -2.0;
    const max = 2.0;
    const offset_regex = /^(\-?\d(\.\d\d?)?)?$/;

    return (offset_regex.test(value) && parseFloat(value) >= min && parseFloat(value) <= max);
  }

  static updateConfirmButton() {
    if (this.isValidScaleInput(this.SCALEINPUT.value) && this.isValidOffsetInput(this.OFFSETINPUT.value))
      this.CONFIRMBUTTON.removeAttribute('disabled');
    else
      this.CONFIRMBUTTON.setAttribute('disabled', true);
  }
}

export { MotorDataInput };
