import configparser
import glob
import os
import time

from byodr.utils import Application, hash_dict, timestamp
from byodr.utils.ipc import JSONPublisher, json_collector

from .robot_comm import *


class ComsApplication(Application):
    def __init__(self, event, config_dir=os.getcwd()):
        """set up configuration directory and a configuration file path

        Args:
            event: allow for thread-safe signaling between processes or threads, indicating when to gracefully shut down or quit certain operations. The TeleopApplication would use this event to determine if it should stop or continue its operations.

            config_dir: specified by the command-line argument --config in the main function. Its default value is set to os.getcwd(), meaning if it's not provided externally, it'll default to the current working directory where the script is run. This directory is where the application expects to find its .ini configuration files.
        """
        super(ComsApplication, self).__init__(quit_event=event)
        self._config_dir = config_dir
        self._config_hash = -1
        self._robot_config_file = None
        self._user_config_file = None
        self._router = Router()
        self._nano = Nano()

    def __check_configuration_files(self):
        _candidates = glob.glob(os.path.join(self._config_dir, "*.ini"))

        for file_path in _candidates:
            # Extract the filename from the path
            file_name = os.path.basename(file_path)

            if file_name == "robot_config.ini":
                self._robot_config_file = file_path
            elif file_name == "config.ini":
                self._user_config_file = file_path

        # Optional: Check if both files were found
        if self._robot_config_file is None or self._user_config_file is None:
            logger.info("Warning: Not all config files were found")

    def _config(self):
        parser = configparser.ConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, "*.ini"))]
        # Get config data related to COMS service (if found) from all the .ini files
        cfg = dict(parser.items("coms")) if parser.has_section("coms") else {}
        return cfg

    def get_user_config_file(self):
        return self._user_config_file

    def get_robot_config_file(self):
        return self._robot_config_file

    def setup(self):
        if self.active():
            self.__check_configuration_files()
            _config = self._config()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash

        # logger.info(tel_data["command"]["robot_config"])
