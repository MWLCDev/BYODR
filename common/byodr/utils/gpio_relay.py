import Jetson.GPIO as GPIO
import threading


class ThreadSafeGpioRelay:
    """
    Thread-safe class for managing a GPIO relay on a Jetson Nano.
    """

    def __init__(self, pin=15):
        self.pin = pin
        self.state = False  # False for OFF, True for ON
        self.lock = threading.Lock()
        GPIO.setmode(GPIO.BOARD)  # Set the pin numbering system to BOARD
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)

    def open(self):
        """Turns the relay ON (sets the GPIO pin high)."""
        with self.lock:
            GPIO.output(self.pin, GPIO.HIGH)
            self.state = True

    def close(self):
        """Turns the relay OFF (sets the GPIO pin low)."""
        with self.lock:
            GPIO.output(self.pin, GPIO.LOW)
            self.state = False

    def toggle(self):
        """Toggles the relay state."""
        with self.lock:
            self.state = not self.state
            GPIO.output(self.pin, GPIO.HIGH if self.state else GPIO.LOW)

    def get_state(self):
        """Returns the current state of the relay."""
        with self.lock:
            return self.state
