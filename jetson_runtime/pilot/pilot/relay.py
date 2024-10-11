from __future__ import absolute_import

import collections
import glob
import logging
import os
from abc import ABCMeta, abstractmethod

import six
from configparser import ConfigParser

from byodr.utils import timestamp
from byodr.utils.ipc import ReceiverThread, JSONZmqClient
from byodr.utils.option import parse_option, hash_dict
from byodr.utils.protocol import MessageStreamProtocol

logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"


class StatusReceiverThreadFactory(object):
    def __init__(self, topic=b"ras/drive/status"):
        self._topic = topic

    def create(self, master_uri):
        return ReceiverThread(url=("{}:5555".format(master_uri)), topic=self._topic)


class PiClientFactory(object):
    def __init__(self):
        pass

    @staticmethod
    def create(master_uri):
        return JSONZmqClient(urls="{}:5550".format(master_uri))


class AbstractRelay(six.with_metaclass(ABCMeta, object)):
    @staticmethod
    def _latest_or_none(candidate, patience):
        _time = 0 if candidate is None else candidate.get("time", 0)
        _on_time = (timestamp() - _time) < patience
        return candidate if _on_time else None

    @abstractmethod
    def setup(self):
        pass

    def step(self, pilot, teleop):
        pass

    def quit(self):
        pass


class NoopMonitoringRelay(AbstractRelay):
    """Fake class made for testing"""

    def setup(self):
        return []

    def step(self, pilot, teleop):
        pass

    def quit(self):
        pass


class RealMonitoringRelay(AbstractRelay):
    def __init__(self, relay, client_factory=None, status_factory=None, config_dir=os.getcwd()):
        super(RealMonitoringRelay, self).__init__()
        self._relay = relay
        self._config_dir = config_dir
        self._integrity = MessageStreamProtocol(max_age_ms=500, max_delay_ms=250)
        self._status_factory = StatusReceiverThreadFactory() if status_factory is None else status_factory
        self._client_factory = PiClientFactory() if client_factory is None else client_factory
        self._relay_closed_calltrace = collections.deque(maxlen=1)
        self._patience_micro = 100.0
        self._config_hash = -1
        self._pi_config = None
        self._pi_client = None
        self._pi_status = None
        self._servo_config = None
        self.n_violations = 0

    def _send_config(self, data):
        if self._pi_client is not None and data is not None:
            self._pi_client.call(dict(time=timestamp(), method="ras/driver/config", data=data))

    def _send_drive(self, throttle=0.0, steering=0.0, reverse_gear=False, wakeup=False):
        if self._pi_client is not None:
            throttle = max(-1.0, min(1.0, throttle))
            steering = max(-1.0, min(1.0, steering))
            _reverse = 1 if reverse_gear else 0
            _wakeup = 1 if wakeup else 0
            self._pi_client.call(dict(time=timestamp(), method="ras/servo/drive", data=dict(steering=steering, throttle=throttle, reverse=_reverse, wakeup=_wakeup)))

    def _drive(self, pilot, teleop):
        pi_status = None if self._pi_status is None else self._pi_status.pop_latest()
        if pi_status is not None and not bool(pi_status.get("configured")):
            self._send_config(self._servo_config)
        if pilot is None:
            self._send_drive()
        else:
            _reverse = teleop and teleop.get("arrow_down", 0)
            _wakeup = teleop and teleop.get("button_b", 0)
            self._send_drive(steering=pilot.get("steering"), throttle=pilot.get("throttle"), reverse_gear=_reverse, wakeup=_wakeup)

    def _config(self):
        parser = ConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, "*.ini"))]
        config_data = {}

        # Loop through all sections and store keys
        for section in parser.sections():
            for key, value in parser.items(section):
                config_data[f"{key}"] = value
        return config_data

    def _on_receive(self, msg):
        self._integrity.on_message(msg.get("time"))

    def setup(self):
        _hash = hash_dict(**self._config())
        if _hash != self._config_hash:
            self._config_hash = _hash
            return self._reboot()
        else:
            return []

    def _reboot(self):
        errors = []
        _config = self._config()
        self._patience_micro = parse_option("patience.ms", int, 100, errors, **_config) * 1000.0
        _pi_uri = parse_option("ras.master.uri", str, "192.168.1.32", errors, **_config)
        _pi_uri = f"tcp://{_pi_uri}"
        # Stopping the sockets that handle communication with the Pi
        if self._pi_client is not None:
            self._pi_client.quit()
        if self._pi_status is not None:
            self._pi_status.quit()
        logger.info("Processing pi at uri '{}'.".format(_pi_uri))
        self._pi_config = _pi_uri
        self._pi_client = self._client_factory.create(_pi_uri)
        self._pi_status = self._status_factory.create(_pi_uri)
        self._pi_status.add_listener(self._on_receive)
        self._pi_status.start()
        _steering_offset = parse_option("ras.driver.steering.offset", float, 0.0, errors, **_config)
        _motor_scale = parse_option("ras.driver.motor.scale", float, 1.0, errors, **_config)
        _motor_alternate = parse_option("ras.driver.motor.alternate", bool, False, errors, **_config)
        _is_gpio_relay = parse_option("driver.gpio_relay", bool, False, errors, **_config)
        self._servo_config = dict(app_version=2, steering_offset=_steering_offset, motor_scale=_motor_scale, is_gpio_relay=_is_gpio_relay, motor_alternate=_motor_alternate)
        self._integrity.reset()
        self._send_config(self._servo_config)
        return errors

    def _open_relay(self):
        self._relay.open()
        self._relay_closed_calltrace.clear()

    def _close_relay(self):
        # In normal operation the relay is constantly asked to close.
        now = timestamp()
        if len(self._relay_closed_calltrace) == 0 or (now - self._relay_closed_calltrace[-1]) > 30 * 1e6:
            self._relay.close()
            self._relay_closed_calltrace.append(now)

    def quit(self):
        self._open_relay()
        if self._pi_client is not None:
            self._pi_client.quit()
        if self._pi_status is not None:
            self._pi_status.quit()

    def step(self, pilot, teleop):
        # Always consume the latest commands.
        c_pilot = self._latest_or_none(pilot, patience=self._patience_micro)
        c_teleop = self._latest_or_none(teleop, patience=self._patience_micro)
        self.n_violations = self._integrity.check()
        if self.n_violations < -5:
            self._close_relay()
            self._drive(c_pilot, c_teleop)
        elif self.n_violations > 200:
            # ZeroMQ ipc over tcp does not allow connection timeouts to be set - while the timeout is too high.
            self._reboot()  # Resets the protocol.
        elif self.n_violations > 5:
            self._open_relay()
            self._drive(None, None)
        else:
            self._drive(None, None)


if __name__ == "__main__":
    logging.basicConfig(format=log_format)
    logging.getLogger().setLevel(logging.INFO)
