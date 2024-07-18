import argparse
import configparser
import glob
import logging
import multiprocessing
import os
import signal

from byodr.utils import Application, hash_dict
from byodr.utils.ipc import json_collector
from fol_utils import FollowingController

logger = logging.getLogger(__name__)

log_format = "%(levelname)s: %(asctime)s %(filename)s:%(lineno)d %(funcName)s %(threadName)s %(message)s"

# Initialize quit event
quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())


class FollowingApplication(Application):
    def __init__(self, event, hz, config_dir=os.getcwd()):
        super(FollowingApplication, self).__init__(quit_event=event, run_hz=hz)
        self._config_dir = config_dir
        self._user_config_file = os.path.join(self._config_dir, "config.ini")
        self._config_hash = -1
        self.controller = FollowingController(model_path="./models/yolov8_20240717_coco(imgsz480x640_FP16).engine", user_config_args=self.get_user_config_file_contents(), event=quit_event, hz=hz)

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

        config_dict = {f"{section}.{option}": value for section in config.sections() for option, value in config.items(section)}
        return config_dict

    def setup(self):
        if self.active():
            self._check_user_config()
            _config = self.get_user_config_file_contents()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash

    def step(self):
        self.controller.request_check()


def main():
    parser = argparse.ArgumentParser(description="Following sockets server.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")
    args = parser.parse_args()

    # Communication sockets.
    teleop_cha = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=quit_event, hwm=1)
    application = FollowingApplication(event=quit_event, config_dir=args.config, hz=20)

    # Getting data from the received sockets declared above
    application.controller.teleop_chatter = lambda: teleop_cha.get()
    application.controller.initialize_following()
    application.setup()
    threads = [teleop_cha]

    if quit_event.is_set():
        return 0

    [t.start() for t in threads]

    try:
        application.run()
    except KeyboardInterrupt:
        quit_event.set()
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        quit_event.set()

    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
