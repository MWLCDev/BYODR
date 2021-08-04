from __future__ import absolute_import

import argparse
import collections
import logging
import os
from abc import ABCMeta, abstractmethod
from configparser import ConfigParser as SafeConfigParser

import odrive
import six
from gpiozero import AngularServo
from odrive.enums import AXIS_STATE_CLOSED_LOOP_CONTROL, AXIS_STATE_IDLE

from byodr.utils import timestamp, Application
from byodr.utils.ipc import JSONPublisher, JSONServerThread
from byodr.utils.option import parse_option
from byodr.utils.protocol import MessageStreamProtocol
from byodr.utils.usbrelay import SearchUsbRelayFactory

logger = logging.getLogger(__name__)
log_format = '%(levelname)s: %(filename)s %(funcName)s %(message)s'


class CommandHistory(object):
    def __init__(self, timeout_seconds=180, hz=25):
        self._threshold = timeout_seconds * hz
        self._num_missing = None
        self.reset()

    def touch(self, steering, throttle, wakeup=False):
        if wakeup:
            self._num_missing = 0
        else:
            has_steering = steering is not None and abs(steering) > 1e-3
            has_throttle = throttle is not None and abs(throttle) > 1e-3
            if not has_steering and not has_throttle:
                self._num_missing += 1
            elif not self.is_missing():
                # After the missing state is reached a wakeup is required to reset.
                self._num_missing = 0

    def reset(self):
        self._num_missing = self._threshold + 1

    def is_missing(self):
        return self._num_missing > self._threshold


class AbstractDriver(six.with_metaclass(ABCMeta, object)):
    def __init__(self, relay):
        self._relay = relay

    @abstractmethod
    def relay_ok(self):
        raise NotImplementedError()

    @abstractmethod
    def relay_violated(self):
        raise NotImplementedError()

    @abstractmethod
    def set_configuration(self, config):
        raise NotImplementedError()

    @abstractmethod
    def is_configured(self):
        raise NotImplementedError()

    @abstractmethod
    def drive(self, steering, throttle):
        raise NotImplementedError()

    @abstractmethod
    def quit(self):
        raise NotImplementedError()


class GPIODriver(AbstractDriver):
    def __init__(self, relay, **kwargs):
        super().__init__(relay)
        # Our relay is expected to be wired on the motor power line.
        self._relay.open()
        self._steer_servo_config = dict(pin=parse_option('servo.steering.pin.nr', int, 0, **kwargs),
                                        min_pw=parse_option('servo.steering.min_pulse_width.ms', float, 0, **kwargs),
                                        max_pw=parse_option('servo.steering.max_pulse_width.ms', float, 0, **kwargs),
                                        frame=parse_option('servo.steering.frame_width.ms', float, 0, **kwargs))
        self._motor_servo_config = dict(pin=parse_option('servo.motor.pin.nr', int, 0, **kwargs),
                                        min_pw=parse_option('servo.motor.min_pulse_width.ms', float, 0, **kwargs),
                                        max_pw=parse_option('servo.motor.max_pulse_width.ms', float, 0, **kwargs),
                                        frame=parse_option('servo.motor.frame_width.ms', float, 0, **kwargs))
        self._steering_config = dict(scale=parse_option('steering.domain.scale', float, 0, **kwargs))
        self._throttle_config = dict(reverse=parse_option('throttle.reverse.gear', int, 0, **kwargs),
                                     forward_shift=parse_option('throttle.domain.forward.shift', float, 0, **kwargs),
                                     backward_shift=parse_option('throttle.domain.backward.shift', float, 0, **kwargs),
                                     scale=parse_option('throttle.domain.scale', float, 0, **kwargs))
        self._steer_servo = None
        self._motor_servo = None

    def _create_servo(self, servo, name, message):
        logger.info("Creating servo {} with config {}".format(name, message))
        if servo is not None:
            servo.close()
        servo = self._angular_servo(message=message)
        return servo

    @staticmethod
    def _angular_servo(message):
        fields = ('pin', 'min_pw', 'max_pw', 'frame')
        m_config = [message.get(f) for f in fields]
        pin, min_pw, max_pw, frame = [m_config[0]] + [1e-3 * x for x in m_config[1:]]
        return AngularServo(pin=pin, min_pulse_width=min_pw, max_pulse_width=max_pw, frame_width=frame)

    @staticmethod
    def _motor_angle(config, throttle):
        _shift = config.get('forward_shift') if throttle > 0 else config.get('backward_shift')
        _angle = min(90, max(-90, _shift + config.get('scale') * throttle))
        return _angle

    def _apply_steering(self, steering):
        if self._steer_servo is not None:
            config = self._steering_config
            scale = config.get('scale')
            self._steer_servo.angle = scale * 90. * min(1, max(-1, steering))

    def _apply_throttle(self, throttle):
        if self._motor_servo is not None:
            config = self._throttle_config
            _angle = self._motor_angle(config, throttle)
            _reverse_boost = config.get('reverse')
            if throttle < -.990 and _reverse_boost < _angle:
                _angle = _reverse_boost
            self._motor_servo.angle = _angle

    def relay_ok(self):
        self._relay.close()

    def relay_violated(self):
        self._relay.open()

    def set_configuration(self, config):
        if config is not None:
            logger.info("Received configuration {}.".format(config))
            _steer_servo_config = self._steer_servo_config
            _motor_servo_config = self._motor_servo_config
            # Translate the values into our domain.
            _steer_servo_config['min_pw'] = 0.5 + .5 * max(-1, min(1, config.get('steering_offset')))
            self._throttle_config['scale'] = max(0, config.get('motor_scale'))
            self._steer_servo = self._create_servo(self._steer_servo, 'steering', _steer_servo_config)
            self._motor_servo = self._create_servo(self._motor_servo, 'motor', _motor_servo_config)

    def is_configured(self):
        return None not in (self._steer_servo, self._motor_servo)

    def drive(self, steering, throttle):
        self._apply_steering(steering)
        self._apply_throttle(throttle)

    def quit(self):
        self._relay.open()
        if self._steer_servo is not None:
            self._steer_servo.close()
        if self._motor_servo is not None:
            self._motor_servo.close()


class ODriveDriver(AbstractDriver):
    def __init__(self, relay, **kwargs):
        super().__init__(relay)
        # Our relay is expected to be wired on the o-drive supply line.
        self._relay.close()
        self._steering_offset = 0
        self._motor_scale = 1
        self._odrive = None

    def _setup(self):
        self._odrive = odrive.find_any(timeout=30)
        assert self._odrive is not None
        self._odrive.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        self._odrive.axis1.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
        logger.info("Setup drive - bus voltage is " + str(self._odrive.vbus_voltage) + "V")

    def relay_ok(self):
        logger.info("Received relay ok.")

    def relay_violated(self):
        logger.info("Received relay violation.")

    def set_configuration(self, config):
        if self._odrive is None:
            self._setup()
        if config is not None:
            logger.info("Received configuration {}.".format(config))
            self._steering_offset = max(-1, min(1, config.get('steering_offset')))
            self._motor_scale = max(0, config.get('motor_scale'))

    def is_configured(self):
        return self._odrive is not None

    def drive(self, steering, throttle):
        pass

    def quit(self):
        self._odrive.axis0.requested_state = AXIS_STATE_IDLE
        self._odrive.axis1.requested_state = AXIS_STATE_IDLE


class MainApplication(Application):
    def __init__(self, chassis=None, hz=10):
        super(MainApplication, self).__init__(run_hz=hz)
        self._chassis = chassis
        self._integrity = MessageStreamProtocol()
        self._cmd_history = CommandHistory(hz=hz)
        self._config_queue = collections.deque(maxlen=1)
        self._drive_queue = collections.deque(maxlen=1)
        self.platform = None
        self.publisher = None

    def _pop_config(self):
        return self._config_queue.popleft() if bool(self._config_queue) else None

    def _pop_drive(self):
        return self._drive_queue.popleft() if bool(self._drive_queue) else None

    def _on_message(self, message):
        self._integrity.on_message(message.get('time'))
        if message.get('method') == 'ras/driver/config':
            self._config_queue.appendleft(message.get('data'))
        else:
            self._drive_queue.appendleft(message.get('data'))

    def setup(self):
        self.platform.add_listener(self._on_message)
        self._integrity.reset()
        self._cmd_history.reset()

    def finish(self):
        self._chassis.quit()

    def step(self):
        n_violations = self._integrity.check()
        if n_violations > 5:
            self._chassis.relay_violated()
            self._integrity.reset()
            return

        c_config, c_drive = self._pop_config(), self._pop_drive()
        self._chassis.set_configuration(c_config)

        v_steering = 0 if c_drive is None else c_drive.get('steering', 0)
        v_throttle = 0 if c_drive is None else c_drive.get('throttle', 0)
        v_wakeup = False if c_drive is None else bool(c_drive.get('wakeup'))

        self._cmd_history.touch(steering=v_steering, throttle=v_throttle, wakeup=v_wakeup)
        if self._cmd_history.is_missing():
            self._chassis.relay_violated()
        elif n_violations < -5:
            self._chassis.relay_ok()

        # Immediately zero out throttle when violations start occurring.
        v_throttle = 0 if n_violations > 0 else v_throttle
        self._chassis.drive(v_steering, v_throttle)
        # Let the communication partner know we are operational.
        self.publisher.publish(data=dict(time=timestamp(), configured=int(self._chassis.is_configured())))


def main():
    parser = argparse.ArgumentParser(description='Steering and throttle driver.')
    parser.add_argument('--config', type=str, default='/config/driver.ini', help='Configuration file.')
    args = parser.parse_args()

    config_file = args.config
    assert os.path.exists(config_file) and os.path.isfile(config_file)

    parser = SafeConfigParser()
    parser.read(config_file)
    kwargs = dict(parser.items('driver'))
    driver_type = parse_option('driver.type', str, **kwargs)

    relay = SearchUsbRelayFactory().get_relay()
    assert relay.is_attached(), "The device is not attached."

    if driver_type == 'gpio':
        driver = GPIODriver(relay, **kwargs)
    elif driver_type == 'odrive':
        driver = ODriveDriver(relay, **kwargs)
    else:
        raise AssertionError("Unknown driver type '{}'.".format(driver_type))

    try:
        application = MainApplication(chassis=driver, hz=25)
        quit_event = application.quit_event

        application.publisher = JSONPublisher(url='tcp://0.0.0.0:5555', topic='ras/drive/status')
        application.platform = JSONServerThread(url='tcp://0.0.0.0:5550', event=quit_event, receive_timeout_ms=50)

        threads = [application.platform]
        if quit_event.is_set():
            return 0

        [t.start() for t in threads]
        application.run()

        logger.info("Waiting on threads to stop.")
        [t.join() for t in threads]
    finally:
        relay.open()


if __name__ == "__main__":
    logging.basicConfig(format=log_format)
    logging.getLogger().setLevel(logging.INFO)
    main()