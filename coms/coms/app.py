import logging
import multiprocessing
import signal, time
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils import timestamp


# This flag starts as false
quit_event = multiprocessing.Event()
quit_event.clear()

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())


# Set the flag as true when we receive interrupt signals
def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


chatter = JSONPublisher(url="ipc:///byodr/coms_c.sock", topic="aav/coms/chatter")
tel_chatter = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=quit_event)
teleop_receiver = json_collector(url="ipc:///byodr/teleop_to_coms.sock", topic=b"aav/teleop/input", event=quit_event)
coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")


def main():
    def chatter_message(cmd):
        """Broadcast message from the current service to any service listening to it. It is a one time message"""
        logger.info(cmd)
        chatter.publish(dict(time=timestamp(), command=cmd))

    threads = [teleop_receiver, tel_chatter]
    [t.start() for t in threads]
    while not quit_event.is_set():
        # Creating a message
        chatter_message("Your command here")

        tel_data = tel_chatter.get()
        if tel_data:
            logger.info(tel_data["command"]["robot_config"])

            # Publishing data in every iteration
        time.sleep(1)
        coms_to_pilot_publisher.publish(teleop_receiver.get())

    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]

    return 0


if __name__ == "__main__":
    # Declaring the logger
    logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger(__name__)
    main()
