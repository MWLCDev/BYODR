import argparse
import configparser
import glob
import logging
import multiprocessing
import os
import signal
import threading
import time

import cv2
import numpy as np
from byodr.utils import Application, hash_dict
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.option import parse_option
from ultralytics import YOLO

from fol_utils import FollowingController


logger = logging.getLogger(__name__)

log_format = "%(levelname)s: %(asctime)s %(filename)s:%(lineno)d %(funcName)s %(threadName)s %(message)s"


signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


quit_event = multiprocessing.Event()


class FollowingApplication(Application):
    def __init__(self, event, hz, config_dir=os.getcwd()):
        super(FollowingApplication, self).__init__(quit_event=event, run_hz=hz)
        self._config_dir = config_dir
        self._user_config_file = os.path.join(self._config_dir, "config.ini")
        self._config_hash = -1

    def _check_user_config(self):
        """See if there is an available user config file, and assign it to the self var"""
        _candidates = glob.glob(os.path.join(self._config_dir, "*.ini"))
        for file_path in _candidates:
            # Extract the filename from the path
            file_name = os.path.basename(file_path)
            if file_name == "config.ini":
                self._user_config_file = file_path

    def get_user_config_file(self):
        return self._user_config_file

    def get_user_config_file_contents(self):
        """Reads the configuration file, flattens the configuration sections and keys"""
        config = configparser.ConfigParser()
        config.read(self.get_user_config_file())

        # Flatten the configuration sections and keys into a single dictionary
        config_dict = {f"{section}.{option}": value for section in config.sections() for option, value in config.items(section)}
        return config_dict

    def setup(self):
        if self.active():
            self._check_user_config()
            _config = self.get_user_config_file_contents()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash


def main():
    parser = argparse.ArgumentParser(description="Following sockets server.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")

    args = parser.parse_args()

    # Communication sockets.
    teleop_cha = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=quit_event, hwm=1)

    application = FollowingApplication(event=quit_event, config_dir=args.config, hz=20)
    controller = FollowingController(model_path="yolov8n.engine", user_config_args=application.get_user_config_file_contents())

    # Sockets used to send data to other services
    controller.publisher = JSONPublisher(url="ipc:///byodr/following.sock", topic="aav/following/controls")

    # Getting data from the received sockets declared above
    controller.teleop_chatter = lambda: teleop_cha.get()
    controller.run()
    application.setup()
    threads = [teleop_cha]

    if quit_event.is_set():
        return 0

    [t.start() for t in threads]

    try:
        application.run()
    except KeyboardInterrupt:
        quit_event.set()

    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
