import logging
import threading

import pyvesc
import serial
from gpiozero import DigitalInputDevice
from pyvesc import GetValues, SetDutyCycle, SetRPM

from BYODR_utils.common import timestamp
from BYODR_utils.common.option import parse_option

logger = logging.getLogger(__name__)


class CommandHistory(object):
    """
    track the history of commands given to the robot (possibly motor commands). It checks for commands that might be 'missing' based on a certain threshold and can be reset.
    """

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


class HallRps(object):
    """This class seems to be related to a Hall sensor (probably for measuring rotations per second, RPS).
    It monitors a specific GPIO pin (pin=16 by default) for changes, likely detecting rotations.
    The sensor's detections are used to calculate rotations per second (rps).
    """

    def __init__(self, pin=16, moment=0.05, debug=False):
        self._moment = moment
        self._debug = debug
        self._lock = threading.Lock()
        self._rps = 0
        self._detect_time = 0
        self._detect_duration = 0
        self._num_detections = 0
        self._sensor = DigitalInputDevice(pin=pin, pull_up=True)
        self._sensor.when_activated = self._detect

    def tick(self):
        with self._lock:
            # Drop to zero when stopped.
            _elapsed = timestamp() - self._detect_time
            if self._detect_duration > 0 and _elapsed / self._detect_duration > 1:
                self._rps *= (1 - self._moment) if self._rps > 1e-2 else 0

    def rps(self):
        with self._lock:
            return self._rps

    def detections(self):
        with self._lock:
            return self._num_detections

    def _detect(self):
        with self._lock:
            _now = timestamp()
            self._detect_duration = _now - self._detect_time
            _rps = 1e6 / self._detect_duration
            self._rps = (self._moment * _rps + (1.0 - self._moment) * self._rps) if self._rps > 0 else _rps
            self._detect_time = _now
            if self._debug:
                self._num_detections += 1


class HallOdometer(object):
    def __init__(self, **kwargs):
        self._cm_per_revolution = parse_option("odometer.distance.cm_per_revolution", float, 15, **kwargs)
        self._debug = parse_option("odometer.debug", int, 0, **kwargs) == 1
        self._alpha = parse_option("odometer.moment.alpha", float, 0.10, **kwargs)
        self._enabled = parse_option("drive.type", str, **kwargs) == "gpio_with_hall"
        self._hall = None

    def is_enabled(self):
        return self._enabled

    def setup(self):
        if self._enabled:
            self._hall = HallRps(moment=self._alpha, debug=self._debug)
            logger.info("Created hall odometer with cm/rev={:2.2f} alpha={:2.2f} and debug={}.".format(self._cm_per_revolution, self._alpha, self._debug))

    def quit(self):
        self._enabled = False
        self._hall = None

    def velocity(self):
        _velocity = self._hall.rps() * self._cm_per_revolution * 1e-2  # Convert to meters per second.
        self._hall.tick()
        if self._debug:
            logger.info("{:2.2f} n={}".format(self._hall.rps(), self._hall.detections()))
        return _velocity


class VESCDrive(object):
    def __init__(self, serial_port="/dev/ttyACM0", rpm_drive=True, cm_per_pole_pair=1):
        self._port = serial_port
        self._rpm_drive = rpm_drive
        self._cm_per_pp = cm_per_pole_pair
        self._lock = threading.Lock()
        self._ser = None

    def _close(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except serial.serialutil.SerialException:
                pass
        self._ser = None

    def _open(self):
        _good = False
        try:
            if self._ser is None:
                self._ser = serial.Serial(self._port, baudrate=115200, timeout=0.05)
                # logger.info("Connected serial port {}.".format(self._port))
            _good = self._ser.isOpen()
        except serial.serialutil.SerialException:
            self._close()
            _good = False
        return _good

    def is_open(self):
        with self._lock:
            return self._open()

    def close(self):
        with self._lock:
            self._close()

    def get_velocity(self):
        return (self.get_rpm() / 60.0) * self._cm_per_pp * 1e-2  # Convert to meters per second.

    def get_rpm(self):
        with self._lock:
            if self._open():
                try:
                    self._ser.write(pyvesc.encode_request(GetValues))
                    if self._ser.in_waiting > 78:
                        (response, consumed) = pyvesc.decode(self._ser.read(79))
                        return response.rpm
                    else:
                        raise AssertionError("Protocol violation on the response length.")
                except serial.serialutil.SerialException:
                    self._close()
                    raise AssertionError("The serial connection is not operational.")

    def set_effort(self, value):
        with self._lock:
            _operational = self._open()
            if _operational:
                try:
                    if self._rpm_drive:
                        self._ser.write(pyvesc.encode(SetRPM(int(value * 1e3))))
                    else:
                        self._ser.write(pyvesc.encode(SetDutyCycle(int(value * 1e4))))
                except serial.serialutil.SerialException:
                    self._close()
                    _operational = False
            return _operational
