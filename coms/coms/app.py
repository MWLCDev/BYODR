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
    socket_manager = SocketManager(quit_event=quit_event)
    tel_chatter = TeleopChatter(application.get_robot_config_file(), application.get_user_config_file())

    application.setup()
    socket_manager.start_threads()

    logger.info("Ready")
    try:
        while not quit_event.is_set():

            socket_manager.coms_to_pilot()
    finally:
        socket_manager.join_threads()

    return 0


if __name__ == "__main__":
    # Declaring the logger
    logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger(__name__)
    main()
