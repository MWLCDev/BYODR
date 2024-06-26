from __future__ import absolute_import

import argparse
import collections
import copy
import logging
import multiprocessing
import os
import shutil
import signal
import subprocess
import time
from abc import ABC, abstractmethod
from configparser import ConfigParser

import numpy as np
from byodr.utils import Application, timestamp
from byodr.utils.ipc import JSONPublisher, JSONServerThread
from byodr.utils.option import parse_option
from byodr.utils.protocol import MessageStreamProtocol
from byodr.utils.usbrelay import SearchUsbRelayFactory, StaticRelayHolder
from gpiozero import AngularServo  # interfacing with the GPIO pins of the Raspberry Pi

from .core import CommandHistory, HallOdometer, VESCDrive

logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s"

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


class AbstractDriver(ABC):
    def __init__(self, relay):
        self._relay = relay

    @staticmethod
    def configuration_check(config):
        version_ok = config is not None and config.get("app_version", -1) == 2
        if config is not None and not version_ok:
            logger.warning("Received incompatible application version - configuration aborted.")
        return version_ok

    @abstractmethod
    def has_sensors(self):
        raise NotImplementedError()

    @abstractmethod
    def relay_ok(self):
        raise NotImplementedError()

    @abstractmethod
    def relay_violated(self, on_integrity=True):
        raise NotImplementedError()

    @abstractmethod
    def set_configuration(self, config):
        raise NotImplementedError()

    @abstractmethod
    def is_configured(self):
        raise NotImplementedError()

    @abstractmethod
    def velocity(self):
        raise NotImplementedError()

    @abstractmethod
    def drive(self, steering, throttle):
        raise NotImplementedError()

    @abstractmethod
    def quit(self):
        raise NotImplementedError()


class NoopDriver(AbstractDriver):
    def __init__(self, relay):
        super().__init__(relay)
        self._relay.close()

    def has_sensors(self):
        return False

    def relay_ok(self):
        pass

    def relay_violated(self, on_integrity=True):
        pass

    def set_configuration(self, config):
        pass

    def is_configured(self):
        return True

    def velocity(self):
        return 0

    def drive(self, steering, throttle):
        return 0

    def quit(self):
        pass


class AbstractSteerServoDriver(AbstractDriver, ABC):
    def __init__(self, relay, **kwargs):
        super().__init__(relay)
        self._steer_servo_config = dict(
            pin=parse_option("servo.steering.pin.nr", int, 13, **kwargs),
            min_pw=parse_option("servo.steering.min_pulse_width.ms", float, 0.5, **kwargs),
            max_pw=parse_option("servo.steering.max_pulse_width.ms", float, 2.5, **kwargs),
            frame=parse_option("servo.steering.frame_width.ms", float, 20.0, **kwargs),
        )
        self._steering_config = dict(scale=parse_option("steering.domain.scale", float, 1.0, **kwargs))
        self._steer_servo = None
        self._last_config = None

    @staticmethod
    def _angular_servo(message):
        fields = ("pin", "min_pw", "max_pw", "frame")
        m_config = [message.get(f) for f in fields]  # Correctly use 'f' as the argument for 'get'
        pin, min_pw, max_pw, frame = [m_config[0]] + [1e-3 * x for x in m_config[1:]]
        return AngularServo(pin=pin, min_pulse_width=min_pw, max_pulse_width=max_pw, frame_width=frame)

    def _create_servo(self, servo, name, message):
        logger.info("Creating servo {} with config {}".format(name, message))
        if servo is not None:
            servo.close()
        servo = self._angular_servo(message=message)
        return servo

    def _apply_steering(self, steering):
        if self._steer_servo is not None:
            scale = self._steering_config.get("scale")
            self._steer_servo.angle = scale * 90.0 * min(1, max(-1, steering))

    def set_configuration(self, config):
        # Translate the values into our domain.
        _steer_servo_config = self._steer_servo_config
        _steer_servo_config["min_pw"] = 0.5 + 0.5 * max(-2, min(2, config.get("steering_offset")))
        if _steer_servo_config != self._last_config:
            self._steer_servo = self._create_servo(self._steer_servo, "steering", _steer_servo_config)
            self._last_config = copy.deepcopy(_steer_servo_config)

    def is_configured(self):
        return self._steer_servo is not None

    def quit(self):
        if self._steer_servo is not None:
            self._steer_servo.close()


class GPIODriver(AbstractSteerServoDriver):
    def __init__(self, relay, **kwargs):
        super().__init__(relay)
        # Our relay is expected to be wired on the motor power line.
        self._relay.open()
        self._motor_servo_config = dict(
            pin=parse_option("servo.motor.pin.nr", int, 12, **kwargs),
            min_pw=parse_option("servo.motor.min_pulse_width.ms", float, 0.5, **kwargs),
            max_pw=parse_option("servo.motor.max_pulse_width.ms", float, 2.5, **kwargs),
            frame=parse_option("servo.motor.frame_width.ms", float, 20.0, **kwargs),
        )
        self._throttle_config = dict(
            reverse=parse_option("throttle.reverse.gear", int, 0.0, **kwargs),
            forward_shift=parse_option("throttle.domain.forward.shift", float, 0.0, **kwargs),
            backward_shift=parse_option("throttle.domain.backward.shift", float, 0.0, **kwargs),
            scale=parse_option("throttle.domain.scale", float, 2.0, **kwargs),
        )
        self._motor_servo = None

    def has_sensors(self):
        return False

    def relay_ok(self):
        self._relay.close()

    def relay_violated(self, on_integrity=True):
        self._relay.open()

    def set_configuration(self, config):
        if self.configuration_check(config):
            logger.info("Received configuration {}.".format(config))
            super().set_configuration(config)
            self._throttle_config["scale"] = max(0, config.get("motor_scale"))
            self._motor_servo = self._create_servo(self._motor_servo, "motor", self._motor_servo_config)

    def is_configured(self):
        return super().is_configured() and self._motor_servo is not None

    def velocity(self):
        raise NotImplementedError()

    def drive(self, steering, throttle):
        self._apply_steering(steering)
        _motor_effort = 0
        if self._motor_servo is not None:
            config = self._throttle_config
            _motor_effort = config.get("scale") * throttle
            _motor_shift = config.get("forward_shift") if throttle > 0 else config.get("backward_shift")
            _motor_angle = min(90, max(-90, _motor_shift + _motor_effort))
            _reverse_boost = config.get("reverse")
            if throttle < -0.990 and _reverse_boost < _motor_angle:
                _motor_effort = _reverse_boost / 90.0
                _motor_angle = _reverse_boost
            self._motor_servo.angle = _motor_angle
        return _motor_effort

    def quit(self):
        self._relay.open()
        super().quit()
        if self._motor_servo is not None:
            self._motor_servo.close()


class SingularVescDriver(AbstractSteerServoDriver):
    def __init__(self, relay, **kwargs):
        super().__init__(relay)
        self._relay.open()
        # Attempt to suppress noise.
        self._velocity = 0.0
        self._velocity_alpha = 0.5
        self._drive = VESCDrive(serial_port=parse_option("drive.serial.port", str, "/dev/ttyACM0", **kwargs), cm_per_pole_pair=parse_option("drive.distance.cm_per_pole_pair", float, 0.88, **kwargs))
        self._throttle_config = dict(scale=parse_option("throttle.domain.scale", float, 2.0, **kwargs))

    def has_sensors(self):
        return self.is_configured()

    def relay_ok(self):
        self._relay.close()

    def relay_violated(self, on_integrity=True):
        if on_integrity:
            self._relay.open()

    def set_configuration(self, config):
        if self.configuration_check(config):
            logger.info("Received configuration {}.".format(config))
            self._throttle_config["scale"] = max(0, config.get("motor_scale"))
            if self._drive.is_open():
                super().set_configuration(config)

    def is_configured(self):
        # This method is polled repeatedly.
        # First check if the drive is open with the side effect that opening is attempted when not in operation.
        return self._drive.is_open() and super().is_configured()

    def velocity(self):
        try:
            self._velocity = self._velocity_alpha * self._velocity + (1 - self._velocity_alpha) * self._drive.get_velocity()
            self._velocity = self._velocity if abs(self._velocity) > 5e-2 else 0
            return self._velocity
        except Exception as e:
            logger.warning(e)
            return 0

    def drive(self, steering, throttle):
        _motor_effort = self._throttle_config.get("scale") * throttle
        _operational = self._drive.set_effort(_motor_effort)
        if _operational:
            self._apply_steering(steering)
        return _motor_effort

    def quit(self):
        self._relay.open()
        super().quit()
        self._drive.close()


class DualVescDriver(AbstractDriver):
    def __init__(self, relay, config_file_dir, **kwargs):
        super().__init__(relay)
        self._relay.close()
        self._config_file_dir = config_file_dir
        self._config_file_path = os.path.join(self._config_file_dir, "drive_config.ini")
        self._previous_motor_alternate = None
        self._pp_cm = parse_option("drive.distance.cm_per_pole_pair", float, 2.3, **kwargs)
        # Initialize with default configuration
        self.update_drive_instances(kwargs)
        self.last_config = None  # Attribute to store the last configuration

        self._steering_offset = 0
        self._steering_effect = max(0.0, float(kwargs.get("drive.steering.effect", 1.8)))
        self._throttle_config = dict(scale=parse_option("throttle.domain.scale", float, 2.0, **kwargs))
        self._axes_ordered = kwargs.get("drive.axes.mount.order", "normal") == "normal"
        self._axis0_multiplier = 1 if kwargs.get("drive.axis0.mount.direction", "forward") == "forward" else -1
        self._axis1_multiplier = 1 if kwargs.get("drive.axis1.mount.direction", "forward") == "forward" else -1

    def update_drive_instances(self, config):
        parser = ConfigParser()
        parser.read(self._config_file_path)

        motor_alternate = config.get("motor_alternate", False)
        if motor_alternate != self._previous_motor_alternate:
            self._previous_motor_alternate = motor_alternate
            # Log and swap the ports
            if motor_alternate:
                port0, port1 = "/dev/ttyACM1", "/dev/ttyACM0"
            else:
                port0, port1 = "/dev/ttyACM0", "/dev/ttyACM1"

            # Update instances with new serial ports
            # Right wheel
            self._drive1 = VESCDrive(serial_port=port0, rpm_drive=False, cm_per_pole_pair=self._pp_cm)
            # Left wheel
            self._drive2 = VESCDrive(serial_port=port1, rpm_drive=False, cm_per_pole_pair=self._pp_cm)

            logger.info("Updated wheel port mapping: drive1={}, drive2={}".format(port0, port1))

    def set_configuration(self, config):
        if config != self.last_config:
            if self.configuration_check(config):
                self._steering_offset = max(-1.0, min(1.0, config.get("steering_offset")))
                self._throttle_config["scale"] = max(0, config.get("motor_scale"))
                self.update_drive_instances(config)
                logger.info("Received new configuration {}.".format(config))
                self.last_config = config  # Update last configuration

    def has_sensors(self):
        return self.is_configured()

    def relay_ok(self):
        self._relay.close()

    def relay_violated(self, on_integrity=True):
        if on_integrity:
            self._relay.open()

    def is_configured(self):
        return self._drive1.is_open() and self._drive2.is_open()

    def velocity(self):
        try:
            return (self._drive1.get_velocity() + self._drive2.get_velocity()) / 2.0
        except Exception as e:
            logger.warning(e)
            return 0

    def drive(self, steering, throttle):
        _motor_scale = self._throttle_config.get("scale")
        # Scale down throttle for one wheel, the other retains its value.
        steering = min(1.0, max(-1.0, steering + self._steering_offset))
        throttle = min(1.0, max(-1.0, throttle))
        effect = 1 - min(1.0, abs(steering) * self._steering_effect)
        left = throttle if steering >= 0 else throttle * effect
        right = throttle if steering < 0 else throttle * effect
        a = (right if self._axes_ordered else left) * self._axis0_multiplier * _motor_scale
        b = (left if self._axes_ordered else right) * self._axis1_multiplier * _motor_scale
        self._drive1.set_effort(a)
        self._drive2.set_effort(b)
        return np.mean([a, b])

    def quit(self):
        self._relay.open()
        self._drive1.close()
        self._drive2.close()


class MainApplication(Application):
    def __init__(self, event, config_file, relay, hz, test_mode=False):
        super(MainApplication, self).__init__(run_hz=hz, quit_event=event)
        self.test_mode = test_mode
        self.config_file_dir = config_file
        self.relay = relay
        self._integrity = MessageStreamProtocol(max_age_ms=100, max_delay_ms=100)
        self._cmd_history = CommandHistory(hz=hz)
        self._config_queue = collections.deque(maxlen=1)
        self._drive_queue = collections.deque(maxlen=4)
        self._last_drive_command = None  # Store the last drive command

        self._chassis = None
        self.platform = None
        self.publisher = None
        self._odometer = None  # Initialize here but set up later

    def setup_components(self):
        # Check configuration files and update, read configuration, then setup odometer and chassis
        self.check_configuration_files()
        kwargs = self.read_configuration()
        self._odometer = HallOdometer(**kwargs)

        drive_type = kwargs.get("drive.type", "unknown")
        if drive_type in ["gpio", "gpio_with_hall"]:
            self._chassis = GPIODriver(self.relay, **kwargs)
        elif drive_type == "vesc_single":
            self._chassis = SingularVescDriver(self.relay, **kwargs)
        elif drive_type == "vesc_dual":
            self._chassis = DualVescDriver(self.relay, self.config_file_dir, **kwargs)
        else:
            raise AssertionError("Unknown drive type '{}'.".format(drive_type))

        self.platform.add_listener(self._on_message)
        self._integrity.reset()
        self._cmd_history.reset()
        self._odometer.setup()

    def check_configuration_files(self):
        """Checks if the configuration file exists, if not, creates it from the template."""
        config_file = "driver.ini"
        template_file_path = "ras/driver.template"

        if not os.path.exists(self.config_file_dir):
            shutil.copyfile(template_file_path, self.config_file_dir)
            logger.info("Created {} from template at {}".format(config_file, self.config_file_dir))

        self._verify_and_add_missing_keys(self.config_file_dir, template_file_path)

    def read_configuration(self):
        parser = ConfigParser()
        parser.read(self.config_file_dir)
        kwargs = {}
        if parser.has_section("driver"):
            kwargs.update(dict(parser.items("driver")))
        if parser.has_section("odometer"):
            kwargs.update(dict(parser.items("odometer")))
        return kwargs

    def _verify_and_add_missing_keys(self, ini_file, template_file):
        config = ConfigParser()
        template_config = ConfigParser()

        config.read(ini_file)
        template_config.read(template_file)

        # Loop through each section and key in the template
        for section in template_config.sections():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in template_config.items(section):
                if not config.has_option(section, key):
                    config.set(section, key, value)
                    logger.info("Added missing key '{}' in section '[{}]' to {}".format(key, section, ini_file))

        # Save changes to the ini file if any modifications have been made
        with open(ini_file, "w") as configfile:
            config.write(configfile)

    def _pop_config(self):
        return self._config_queue.popleft() if bool(self._config_queue) else None

    def _pop_drive(self):
        """Get one command from one end of the drive queue"""
        # This case happens when booting for the first time and PIL didn't send anything yet
        if not self._drive_queue:
            if self._last_drive_command:
                # If the queue is empty and there's a last known command, return it instead of None
                return self._last_drive_command
            else:
                # A default command if no commands have ever been received
                return {"steering": 0.0, "throttle": 0.0, "reverse": 0, "wakeup": 0}
        else:
            # Pop the command from the queue and update the last known command
            self._last_drive_command = self._drive_queue.popleft()
            return self._last_drive_command

    def _on_message(self, message):
        self._integrity.on_message(message.get("time"))
        if message.get("method") == "ras/driver/config":
            self._config_queue.appendleft(message.get("data"))
        else:
            self._drive_queue.appendleft(message.get("data"))

    def finish(self):
        self._chassis.quit()
        self._odometer.quit()

    def step(self):
        n_violations = self._integrity.check()
        if n_violations > 5:
            self._chassis.relay_violated(on_integrity=True)
            self._integrity.reset()
            return

        c_config, c_drive = self._pop_config(), self._pop_drive()
        # print(c_drive)
        self._chassis.set_configuration(c_config)

        v_steering = 0 if c_drive is None else c_drive.get("steering", 0)
        v_throttle = 0 if c_drive is None else c_drive.get("throttle", 0)
        v_wakeup = False if c_drive is None else bool(c_drive.get("wakeup"))

        self._cmd_history.touch(steering=v_steering, throttle=v_throttle, wakeup=v_wakeup)
        if self._cmd_history.is_missing():
            self._chassis.relay_violated(on_integrity=False)
        elif n_violations < -5:
            self._chassis.relay_ok()

        # Immediately zero out throttle when violations start occurring.
        v_throttle = 0 if n_violations > 0 else v_throttle
        _effort = self._chassis.drive(v_steering, v_throttle)
        _data = dict(time=timestamp(), configured=int(self._chassis.is_configured()), motor_effort=_effort)
        if self._chassis.has_sensors():
            _data.update(dict(velocity=self._chassis.velocity()))
        elif self._odometer.is_enabled():
            _data.update(dict(velocity=self._odometer.velocity()))

        # Let the communication partner know we are operational.
        self.publisher.publish(data=_data)


def main():
    parser = argparse.ArgumentParser(description="Steering and throttle driver.")
    parser.add_argument("--config", type=str, default="/config/driver.ini", help="Configuration file.")
    args = parser.parse_args()

    config_file = args.config

    _relay = SearchUsbRelayFactory().get_relay()
    ras_dynamic_ip = subprocess.check_output("hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'", shell=True).decode().strip().split()[0]
    assert _relay.is_attached(), "The relay device is not attached."

    holder = StaticRelayHolder(relay=_relay)
    try:

        application = MainApplication(quit_event, config_file, relay=holder, hz=50)

        application.publisher = JSONPublisher(url="tcp://{}:5555".format(ras_dynamic_ip), topic="ras/drive/status")
        application.platform = JSONServerThread(url="tcp://{}:5550".format(ras_dynamic_ip), event=quit_event, receive_timeout_ms=50)
        application.setup_components()  # Set up components including reading the config

        threads = [application.platform]
        if quit_event.is_set():
            return 0

        [t.start() for t in threads]
        application.run()

        logger.info("Waiting on threads to stop.")
        [t.join() for t in threads]
    finally:
        holder.open()

    while not quit_event.is_set():
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
