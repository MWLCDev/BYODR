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


class SocketManager():
    def __init__(self, quit_event):
        self.quit_event = quit_event
        # Initialize sockets as instance variables
        self.coms_chatter = JSONPublisher(url="ipc:///byodr/coms_c.sock", topic="aav/coms/chatter")
        self.tel_chatter_socket = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=quit_event)
    
        self.threads = [self.tel_chatter_socket]

    def get_teleop_chatter(self):
        while not self.quit_event.is_set():
            return self.tel_chatter_socket.get()

    def chatter_message(self, cmd):
        """Broadcast message from COMS chatter with a timestamp. It is a one time message"""
        logger.info(cmd)
        self.coms_chatter.publish(dict(time=timestamp(), command=cmd))

    def start_threads(self):
        for thread in self.threads:
            thread.start()
        logger.info("Started all communication sockets")

    def join_threads(self):
        for thread in self.threads:
            thread.join()


class IntersegmentCommunication:
    def __init__(self, quit_event):
        self.quit_event = quit_event

        # Initialize sockets as instance variables

        # Other socket located on pilot/app.py/140
        # Socket that forwards movement commands to Pilot
        self.coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

        # Other socket located on teleop/app.py/306
        # Socket that receives movement commands from Teleop
        self.teleop_receiver = json_collector(url="ipc:///byodr/teleop_to_coms.sock", topic=b"aav/teleop/input", event=quit_event)

        # Other socket located on vehicles/rover/app.py/59
        # Socket that receives velocity from Vehicle
        self.vehicle_receiver = json_collector(url='ipc:///byodr/velocity_to_coms.sock', topic=b'ras/drive/velocity', event=quit_event)

        
        self.threads = [self.teleop_receiver, self.vehicle_receiver]


    def publish_to_pilot(self, message):
        # Method to publish a message using coms_to_pilot_publisher
        self.coms_to_pilot_publisher.publish(message)

    def get_velocity(self):
        # Method to get data from vehicle_receiver
        while not self.quit_event.is_set():
            return self.vehicle_receiver.get()

    def get_movement_command(self):
        # Method to get data from teleop_receiver
        while not self.quit_event.is_set():
            return self.teleop_receiver.get()

    def start_threads(self):
        for thread in self.threads:
            thread.start()
        logger.info("Started all communication sockets")

    def join_threads(self):
        for thread in self.threads:
            thread.join()
