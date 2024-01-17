from __future__ import absolute_import

import argparse
import collections
import glob
import logging
import os
from abc import ABCMeta, abstractmethod
import six
from six.moves.configparser import SafeConfigParser

from byodr.utils import timestamp
from byodr.utils.ipc import ReceiverThread, JSONZmqClient
from byodr.utils.option import parse_option, hash_dict
from byodr.utils.protocol import MessageStreamProtocol
from byodr.utils.usbrelay import SingleChannelUsbRelay

logger = logging.getLogger(__name__)
log_format = '%(levelname)s: %(filename)s %(funcName)s %(message)s'




def execute(arguments):
    _device = SingleChannelUsbRelay()
    _device.attach()

    _cmd = arguments.cmd
    if _cmd == 'open':
        _device.open()
    elif _cmd == 'close':
        _device.close()
    else:
        raise AssertionError("Invalid command string '{}'.".format(_cmd))


# Class that is receiving a status of the pi
class StatusReceiverThreadFactory(object):
    def __init__(self, topic=b'ras/drive/status'):
        self._topic = topic

    def create(self, master_uri):
        return ReceiverThread(url=('{}:5555'.format(master_uri)), topic=self._topic)


# Class that is sending commands to the pi
class PiClientFactory(object):
    def __init__(self):
        pass

    @staticmethod
    def create(master_uri):
        return JSONZmqClient(urls='{}:5550'.format(master_uri))


class AbstractRelay(six.with_metaclass(ABCMeta, object)):
    @staticmethod
    def _latest_or_none(candidate, patience):
        _time = 0 if candidate is None else candidate.get('time')
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
    def setup(self):
        return []

    def step(self, pilot, teleop):
        pass

    def quit(self):
        pass

# Class that handles the functionality of the sending/receiving functions of this service.
# Also controls the relay (green relay connected to the pi and nano)
class RealMonitoringRelay(AbstractRelay):
    def __init__(self, relay, client_factory=None, status_factory=None, config_dir=os.getcwd()):
        super(RealMonitoringRelay, self).__init__()
        self._relay = relay
        self._config_dir = config_dir
        self._integrity = MessageStreamProtocol() # The variable that returns the communication errors with the Pi
        self._status_factory = StatusReceiverThreadFactory() if status_factory is None else status_factory
        self._client_factory = PiClientFactory() if client_factory is None else client_factory
        self._relay_closed_calltrace = collections.deque(maxlen=1)
        self._patience_micro = 100.
        self._config_hash = -1
        self._pi_config = None
        self._pi_client = None
        self._pi_status = None
        self._servo_config = None

        
    # Sends the config to the Pi
    def _send_config(self, data):
        if self._pi_client is not None and data is not None:
            self._pi_client.call(dict(time=timestamp(),
                                      method='ras/driver/config',
                                      data=data))

    # Sends the movement commands to the Pi
    def _send_drive(self, throttle=0., steering=0., reverse_gear=False, wakeup=False):
        if self._pi_client is not None:
            throttle = max(-1., min(1., throttle))
            steering = max(-1., min(1., steering))
            _reverse = 1 if reverse_gear else 0
            _wakeup = 1 if wakeup else 0
            
            # Sending data to the Pi
            self._pi_client.call(dict(time=timestamp(),
                                      method='ras/servo/drive',
                                      data=dict(steering=steering, throttle=throttle, reverse=_reverse, wakeup=_wakeup)))


    def _drive(self, pilot, coms):
        pi_status = None if self._pi_status is None else self._pi_status.pop_latest()

        # Checking if the Pi is setup according to the configuration we sent
        if pi_status is not None and not bool(pi_status.get('configured')):
            self._send_config(self._servo_config)

        # Checking the source of the commands that we are about to send to the Pi
        if pilot is None:
            self._send_drive()
        else:
            _reverse = coms and coms.get('arrow_down', 0)
            _wakeup = coms and coms.get('button_b', 0)
            self._send_drive(steering=pilot.get('steering'), throttle=pilot.get('throttle'), reverse_gear=_reverse, wakeup=_wakeup)

    def _config(self):
        parser = SafeConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, '*.ini'))]
        return dict(parser.items('vehicle')) if parser.has_section('vehicle') else {}

    # Function that runs whenever the Nano receives a config reply from the Pi
    def _on_receive(self, msg):
        self._integrity.on_message(msg.get('time'))

    def setup(self):
        _hash = hash_dict(**self._config())
        if _hash != self._config_hash:
            self._config_hash = _hash
            return self._reboot()
        else:
            return []

    # Restarting the functions of this file
    def _reboot(self):
        errors = []
        _config = self._config()
        self._patience_micro = parse_option('patience.ms', int, 100, errors, **_config) * 1000.
        _pi_uri = parse_option('ras.master.uri', str, 'tcp://192.168.1.32', errors, **_config)
        _pi_uri = f"tcp://{_pi_uri}"
        # Stopping the sockets that handle communication with the Pi
        if self._pi_client is not None:
            self._pi_client.quit()
        if self._pi_status is not None:
            self._pi_status.quit()
        
        # Restarting the sockets that handle communication with the Pi
        logger.info("Processing pi at uri '{}'.".format(_pi_uri))
        self._pi_config = _pi_uri
        self._pi_client = self._client_factory.create(_pi_uri)
        self._pi_status = self._status_factory.create(_pi_uri)
        self._pi_status.add_listener(self._on_receive)
        self._pi_status.start()

        # Resending the config to the Pi
        _steering_offset = parse_option('ras.driver.steering.offset', float, 0.0, errors, **_config)
        _motor_scale = parse_option('ras.driver.motor.scale', float, 1.0, errors, **_config)
        self._servo_config = dict(app_version=2, steering_offset=_steering_offset, motor_scale=_motor_scale)
        self._integrity.reset()
        self._send_config(self._servo_config)
        return errors

    # Opens the relays connected to the Nano. Open => no flow of current 
    def _open_relay(self):
        self._relay.open()
        self._relay_closed_calltrace.clear()

    # Closes the relays connected to the Nano. Closed => flow of current 
    def _close_relay(self):
        # In normal operation the relay is constantly asked to close.
        now = timestamp()
        if len(self._relay_closed_calltrace) == 0 or (now - self._relay_closed_calltrace[-1]) > 30 * 1e6:
            self._relay.close()
            self._relay_closed_calltrace.append(now)

    # Closing the sockets that handle communication with the Pi
    def quit(self):
        self._open_relay()
        if self._pi_client is not None:
            self._pi_client.quit()
        if self._pi_status is not None:
            self._pi_status.quit()

    # Function that will be executed in a loop. It is called in the app.py file, not here
    # Gets commands from coms and pilot and then checks for any communication errors between itsef and the Pi
    def step(self, pilot, coms):
        # Always consume the latest commands.
        c_pilot = self._latest_or_none(pilot, patience=self._patience_micro)
        c_coms = self._latest_or_none(coms, patience=self._patience_micro)
        # logger.info(f"Processing with : {c_pilot}, {c_coms}.")
        # logger.info(f"Processing with : {c_pilot}")

        n_violations = self._integrity.check()

        # If the Pi is responding normally
        if n_violations < -5:
            self._close_relay()
            self._drive(c_pilot, c_coms)
        # If the Pi is not responding
        elif n_violations > 200:
            # ZeroMQ ipc over tcp does not allow connection timeouts to be set - while the timeout is too high.
            self._reboot()  # Resets the protocol.
        # If there are errors and delayes in the communication with the Pi, we open the relays
        elif n_violations > 5:
            self._open_relay()
            self._drive(None, None)
        else:
            self._drive(None, None)


def main():

    
    parser = argparse.ArgumentParser(description='Spdt usb relay.')
    subparsers = parser.add_subparsers(help='Methods.')

    parser_a = subparsers.add_parser('exec', help='Open or close the relay.')
    parser_a.add_argument('--cmd', type=str, required=True, help='Open or close the relay.')
    parser_a.set_defaults(func=execute)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    logging.basicConfig(format=log_format)
    logging.getLogger().setLevel(logging.INFO)
    main()
