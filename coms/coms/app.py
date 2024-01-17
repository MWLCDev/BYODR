import logging
import multiprocessing
import signal
from byodr.utils.ipc import JSONPublisher, json_collector

# This flag starts as false
quit_event = multiprocessing.Event()
quit_event.clear()

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())


# Set the flag as true when we receive interrupt signals
def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


# Declaring the logger
logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)
coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

teleop_receiver = json_collector(url="ipc:///byodr/teleop_to_coms.sock", topic=b"aav/teleop/input", event=quit_event)


def main():
    teleop_receiver.start()

    while not quit_event.is_set():
        while not quit_event.is_set():
            coms_to_pilot_publisher.publish(teleop_receiver.get())

    return 0


if __name__ == "__main__":
    main()
