from __future__ import absolute_import

import RPi.GPIO as GPIO
import threading


class ThreadSafePi4GpioRelay:
    """Thread-safe class for managing a GPIO relay on a Raspberry Pi."""

    def __init__(self, pin=15):
        self.pin = pin
        self.state = False  # False for OFF, True for ON
        self.lock = threading.Lock()
        GPIO.setmode(GPIO.BOARD)  # Set the pin numbering system to BOARD
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)

    def open(self):
        """Turns the relay ON (sets the GPIO pin LOW)."""
        with self.lock:
            GPIO.output(self.pin, GPIO.LOW)
            self.state = False

    def close(self):
        """Turns the relay OFF (sets the GPIO pin HIGH)."""
        with self.lock:
            GPIO.output(self.pin, GPIO.HIGH)
            self.state = True

    def toggle(self):
        """Toggles the relay state."""
        with self.lock:
            self.state = not self.state
            GPIO.output(self.pin, GPIO.LOW if self.state else GPIO.HIGH)

    def get_state(self):
        """Returns the current state of the relay."""
        with self.lock:
            return self.state
    
    def cleanup(self):
        """Cleans up the GPIO state."""
        GPIO.cleanup(self.pin)
