from __future__ import absolute_import

import argparse
import collections
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
from BYODR_utils.common import Application, timestamp
from BYODR_utils.common.ipc import JSONPublisher, JSONServerThread
from BYODR_utils.common.option import parse_option
from BYODR_utils.common.protocol import MessageStreamProtocol
from BYODR_utils.common.usbrelay import SearchUsbRelayFactory
from BYODR_utils.PI_specific.gpio_relay import ThreadSafePi4GpioRelay

from ras.core import CommandHistory, HallOdometer, VESCDrive

logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(asctime)s %(filename)s:%(lineno)d %(funcName)s %(threadName)s %(message)s"

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


class DummyRelay:
    def open(self):
        pass

    def close(self):
        pass


class AbstractDriver(ABC):
    def __init__(self):
        self._relay = None

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


class ConfigFile:
    def __init__(self, config_dir):
        self._config_dir = config_dir
        self.driver_config_dir = os.path.join(self._config_dir, "driver.ini")
        self.driver_config_parser = ConfigParser()
        self.check_configuration_files()

    def check_configuration_files(self):
        """Checks if the configuration file exists, if not, creates it from the template."""
        config_file = "driver.ini"
        template_file_path = "ras/driver.template"

        if not os.path.exists(self.driver_config_dir):
            shutil.copyfile(template_file_path, self.driver_config_dir)
            logger.info("Created {} from template at {}".format(config_file, self.driver_config_dir))

        self._verify_and_add_missing_keys(self.driver_config_dir, template_file_path)

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
        with open(ini_file, "w") as config_file:
            config.write(config_file)

    def read_configuration(self):
        self.driver_config_parser.read(self.driver_config_dir)
        servos_file_arguments = {}
        if self.driver_config_parser.has_section("driver"):
            servos_file_arguments.update(dict(self.driver_config_parser.items("driver")))
        if self.driver_config_parser.has_section("odometer"):
            servos_file_arguments.update(dict(self.driver_config_parser.items("odometer")))
        return servos_file_arguments


class DualVescDriver(AbstractDriver):
    def __init__(self, config_file):
        super().__init__()
        self._previous_motor_alternate = None
        self.last_config = None  # Attribute to store the last configuration received from the nano
        self._steering_offset = 0
        self._relay = DummyRelay()  # Initialize the relay with a default type to avoid triggering violations prematurely.
        self.driver_config = config_file.read_configuration()

        self._setup_driver_configs()
        self.update_drive_instances(self.driver_config)
        self._relay.close()

    def _setup_driver_configs(self):
        self._pp_cm = parse_option("drive.distance.cm_per_pole_pair", float, 2.3, **self.driver_config)
        self._max_km_speed = parse_option("drive.throttle.max_km", float, 7, **self.driver_config)
        self._steering_effect = max(0.0, float(self.driver_config.get("drive.steering.effect", 1.8)))
        self._throttle_config = dict(scale=parse_option("throttle.domain.scale", float, 2.0, **self.driver_config))
        self._axes_ordered = self.driver_config.get("drive.axes.mount.order", "normal") == "normal"
        self._axis0_multiplier = 1 if self.driver_config.get("drive.axis0.mount.direction", "forward") == "forward" else -1  # Left wheel
        self._axis1_multiplier = 1 if self.driver_config.get("drive.axis1.mount.direction", "forward") == "forward" else -1  # Reft wheel

    def _check_relay_type(self, is_gpio_relay):
        """Decide on the relay type based on configuration and initialize it."""
        try:
            if is_gpio_relay:
                self._relay = ThreadSafePi4GpioRelay()
                logger.info("Initialized GPIO Relay")
            else:
                self._relay = SearchUsbRelayFactory().get_relay()
                logger.info("Initialized USB Relay")
                # assert self._relay.is_attached(), "The relay device is not attached."
        except AssertionError as e:
            logger.error("Relay initialization error: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error during relay type checking: %s", e)
            raise

    def update_drive_instances(self, config):
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
                self._check_relay_type(config.get("is_gpio_relay"))
                logger.info("Received new configuration {}.".format(config))
                self.last_config = config

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
        logger.info(throttle)
        _motor_scale = self._throttle_config.get("scale")
        # Scale down throttle for one wheel, the other retains its value.
        steering = min(1.0, max(-1.0, steering + self._steering_offset))
        throttle = min(1.0, max(-1.0, throttle))
        effect = 1 - min(1.0, abs(steering) * self._steering_effect)
        left = throttle if steering >= 0 else throttle * effect
        right = throttle if steering < 0 else throttle * effect
        raw_a = (right if self._axes_ordered else left) * self._axis0_multiplier * _motor_scale
        raw_b = (left if self._axes_ordered else right) * self._axis1_multiplier * _motor_scale
        # Clamp efforts if they might exceed expected values. Not to damage the fuses.
        # Max speed of 10Km/h
        a = max(-self._max_km_speed, min(self._max_km_speed, raw_a))
        b = max(-self._max_km_speed, min(self._max_km_speed, raw_b))
        self._drive1.set_effort(a)
        self._drive2.set_effort(b)
        return np.mean([a, b])

    def quit(self):
        self._relay.open()
        self._drive1.close()
        self._drive2.close()


class MainApplication(Application):
    def __init__(self, event, config_dir, hz, test_mode=False):
        super(MainApplication, self).__init__(run_hz=hz, quit_event=event)
        self.test_mode = test_mode
        self._integrity = MessageStreamProtocol(max_age_ms=200, max_delay_ms=200)
        self._cmd_history = CommandHistory(hz=hz)
        self._config_queue = collections.deque(maxlen=1)
        self._drive_queue = collections.deque(maxlen=4)
        self._last_drive_command = None
        self._chassis = None
        self.platform = None
        self.publisher = None
        self._odometer = None

        # Instantiate ConfigFile
        self.config_file = ConfigFile(config_dir)

    def setup_components(self):
        kwargs = self.config_file.read_configuration()

        self._odometer = HallOdometer(**kwargs)

        drive_type = kwargs.get("drive.type", "unknown")
        if drive_type == "vesc_dual":
            self._chassis = DualVescDriver(self.config_file)
        else:
            raise AssertionError("Unknown drive type '{}'.".format(drive_type))

        self.platform.add_listener(self._on_message)
        self._integrity.reset()
        self._cmd_history.reset()
        self._odometer.setup()

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
    parser.add_argument("--config", type=str, default="/config", help="Configuration file.")
    args = parser.parse_args()

    ras_dynamic_ip = subprocess.check_output("hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'", shell=True).decode().strip().split()[0]

    try:
        application = MainApplication(quit_event, args.config, hz=50)
        application.publisher = JSONPublisher(url="tcp://{}:5555".format(ras_dynamic_ip), topic="ras/drive/status")
        application.platform = JSONServerThread(url="tcp://{}:5550".format(ras_dynamic_ip), event=quit_event, receive_timeout_ms=50)
        application.setup_components()

        threads = [application.platform]
        if quit_event.is_set():
            return 0

        [t.start() for t in threads]
        application.run()

        logger.info("Waiting on threads to stop.")
        [t.join() for t in threads]
    finally:
        application._chassis._relay.open()

    while not quit_event.is_set():
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
