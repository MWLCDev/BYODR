import argparse
import configparser
import glob
import logging
import multiprocessing
import os
import signal
import time

from byodr.utils import Application, hash_dict, timestamp
from byodr.utils.ipc import JSONPublisher, json_collector

from .robot_comm import *
from .common_utils import *

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


class TeleopChatter:
    """Resolve the data incoming from Teleop chatter socket"""

    def __init__(self, _robot_config_dir, _segment_config_dir):
        self.robot_config_dir = _robot_config_dir
        self.seg_config_dir = _segment_config_dir
        self.robot_actions = RobotActions(self.robot_config_dir)

        logger.info(tel_data["command"]["robot_config"])


def chatter_message(cmd):
    """Broadcast message from the current service to any service listening to it. It is a one time message"""
    logger.info(cmd)
    chatter.publish(dict(time=timestamp(), command=cmd))


def main():
    # Adding the parser here for a static design pattern between all services
    parser = argparse.ArgumentParser(description="Communication sockets server.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")
    args = parser.parse_args()

    application = ComsApplication(event=quit_event, config_dir=args.config)
    application.setup()
    [t.start() for t in threads]
    while not quit_event.is_set():
        # Creating a message
        # chatter_message("Check message to TEL")
        # time.sleep(1)

        tel_data = tel_chatter.get()
        tel_chatter_filter_robot(tel_data)

        # Publishing data in every iteration
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
