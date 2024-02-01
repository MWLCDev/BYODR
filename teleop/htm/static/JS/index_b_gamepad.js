//serves as a base or default controller
var NoneController = {
  gamepad_index: 0,
  steering: 0,
  throttle: 0,
  pan: 0,
  tilt: 0,
  button_y: 0,
  button_b: 0,
  button_x: 0,
  button_a: 0,
  button_left: 0,
  button_right: 0,
  button_center: 0,
  arrow_up: 0,
  arrow_down: 0,
  arrow_left: 0,
  arrow_right: 0,
  healthy: false,

  reset: function () {
    this.healthy = false;
  },

  collapse: function (value, zone = 0) {
    result = Math.abs(value) <= zone ? 0 : value > 0 ? value - zone : value + zone;
    // Scale back.
    return result / (1 - zone);
  },

  gamepad: function () {
    return navigator.getGamepads()[this.gamepad_index];
  },

  set_throttle: function (left_trigger, right_trigger) {
    // Observed gamepads which reported half-full throttle before use of any buttons.
    if (!this.healthy && left_trigger < 0.01 && right_trigger < 0.01) {
      this.healthy = true;
    }
    if (this.healthy) {
      this.throttle = right_trigger > 0.01 ? -1 * right_trigger : left_trigger;
    } else {
      this.throttle = 0;
    }
  },

  poll: function () {
    return false;
  }
}

var Xbox360StandardController = extend(NoneController, {
  threshold: 0.195,

  poll: function () {
    pad = this.gamepad();
    if (pad != undefined) {
      this.set_throttle(pad.buttons[6].value, pad.buttons[7].value)
      this.steering = this.collapse(pad.axes[2], this.threshold);
      this.pan = this.collapse(pad.axes[0], this.threshold);
      this.tilt = this.collapse(pad.axes[1], this.threshold);
      this.button_y = pad.buttons[3].value;
      this.button_b = pad.buttons[1].value;
      this.button_x = pad.buttons[2].value;
      this.button_a = pad.buttons[0].value;
      this.button_left = pad.buttons[4].value;
      this.button_right = pad.buttons[5].value;
      this.button_center = pad.buttons[16].value;
      this.arrow_up = pad.buttons[12].value;
      this.arrow_down = pad.buttons[13].value;
      this.arrow_left = pad.buttons[14].value;
      this.arrow_right = pad.buttons[15].value;
    }
    return this.healthy;
  }
});

var PS4StandardController = extend(NoneController, {
  threshold: 0.09,

  poll: function () {
    // On ubuntu 18 under chrome button 17 does not exist - use button 16.
    pad = this.gamepad();
    if (pad != undefined) {
      this.set_throttle(pad.buttons[6].value, pad.buttons[7].value)
      this.steering = this.collapse(pad.axes[2], this.threshold);
      this.pan = this.collapse(pad.axes[0], this.threshold);
      this.tilt = this.collapse(pad.axes[1], this.threshold);
      this.button_y = pad.buttons[3].value;
      this.button_b = pad.buttons[1].value;
      this.button_x = pad.buttons[2].value;
      this.button_a = pad.buttons[0].value;
      this.button_left = pad.buttons[4].value;
      this.button_right = pad.buttons[5].value;
      this.button_center = pad.buttons[16].value;
      this.arrow_up = pad.buttons[12].value;
      this.arrow_down = pad.buttons[13].value;
      this.arrow_left = pad.buttons[14].value;
      this.arrow_right = pad.buttons[15].value;
    }
    return this.healthy;
  }
});

var gamepad_controller = {
  controller: Object.create(NoneController),

  _create_gamepad: function (gamepad) {
    // 45e-28e-Xbox 360 Wired Controller / Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 02fd)
    // Wireless Controller (STANDARD GAMEPAD Vendor: 054c Product: 09cc)
    var gid = gamepad.id;
    var result = null;
    if (gamepad.mapping == 'standard' && gid.includes('45e')) {
      result = Object.create(Xbox360StandardController);
    } else if (gamepad.mapping == 'standard') {
      result = Object.create(PS4StandardController);
    }
    if (result) {
      result.gamepad_index = gamepad.index;
    }
    return result;
  },
  // Handle gamepad connections. When a gamepad connects, it checks if the gamepad is supported, then assigns the appropriate controller type (Xbox360StandardController or PS4StandardController) to the gamepad_controller object
  _connect: function (gamepad, connecting) {
    if (connecting) {
      controller = this._create_gamepad(gamepad);
      if (controller != undefined) {
        this.controller = controller;
        console.log("Connected " + gamepad.id + " - mapping = '" + gamepad.mapping + "'.");
      } else {
        console.log("Gamepad " + gamepad.id + " - mapping = '" + gamepad.mapping + "' not supported.");
      }
    } else {
      this.controller = Object.create(NoneController);
      console.log("Disconnected " + gamepad.id + ".");
    }
  },

  is_active: function () {
    return this.controller.poll();
  },

  reset: function () {
    this.controller.reset();
  },

  get_command: function () {
    const ct = this.controller;
    // Skip buttons when not pressed to save bandwidth.
    var command = {};
    command.steering = ct.steering;
    command.throttle = ct.throttle;
    command.pan = ct.pan;
    command.tilt = ct.tilt;
    if (ct.button_center) {
      command.button_center = ct.button_center;
    }
    if (ct.button_left) {
      command.button_left = ct.button_left;
    }
    if (ct.button_right) {
      command.button_right = ct.button_right;
    }
    if (ct.button_a) {
      command.button_a = ct.button_a;
    }
    if (ct.button_b) {
      command.button_b = ct.button_b;
    }
    if (ct.button_x) {
      command.button_x = ct.button_x;
    }
    if (ct.button_y) {
      command.button_y = ct.button_y;
    }
    if (ct.arrow_up) {
      command.arrow_up = ct.arrow_up;
    }
    if (ct.arrow_down) {
      command.arrow_down = ct.arrow_down;
    }
    if (ct.arrow_left) {
      command.arrow_left = ct.arrow_left;
    }
    if (ct.arrow_right) {
      command.arrow_right = ct.arrow_right;
    }
    return command;
  }
}

window.addEventListener("gamepadconnected", function (e) { gamepad_controller._connect(e.gamepad, true); }, false);
window.addEventListener("gamepaddisconnected", function (e) { gamepad_controller._connect(e.gamepad, false); }, false);
