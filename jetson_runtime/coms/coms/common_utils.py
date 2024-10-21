import configparser
import glob
import os
import time

from BYODR_utils.common import Application, hash_dict, timestamp
from BYODR_utils.common.ipc import JSONPublisher, json_collector

from .robot_comm import *


class RepeatedTimer(object):
    """
    A timer that runs a function at regular intervals.

    This class creates a timer that executes a specified function every 'interval' seconds.
    The timer runs in its own thread and checks for a 'quit_event' to determine whether to continue execution or stop.

    Attributes:
        interval (float): The time interval, in seconds, between each execution of the function.
        function (callable): The function to be executed at each interval.
        quit_event (multiprocessing.Event): An event that signals the timer to stop running when set.
        args (tuple): Additional positional arguments to pass to the function.
        kwargs (dict): Additional keyword arguments to pass to the function.
        timer (threading.Timer): Internal timer instance for scheduling function execution.
        running (bool): Indicates whether the timer is currently running.

    Methods:
        start(): Starts the timer, scheduling the function to be executed at regular intervals.
        stop(): Stops the timer, preventing any further execution of the function.

    Usage:
        To use this class, instantiate it with the desired interval, function, and quit_event.
        Call the start() method to begin the timer. The timer will automatically stop when the quit_event is set,
        or the stop() method can be called explicitly to stop it.
    """

    def __init__(self, interval, function, quit_event, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.quit_event = quit_event
        self.args = args
        self.kwargs = kwargs
        self.timer = None
        self.running = False
        self.start()

    def _run(self):
        if not self.quit_event.is_set():
            self.running = False
            self.start()
            self.function(*self.args, **self.kwargs)
        else:
            self.running = False

    def start(self):
        if not self.running:
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()
            self.running = True

    def stop(self):
        self.timer.cancel()
        self.running = False


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

    def check_and_start_SUB(self):
        """Start subscriber ZMQ socket between segments if there is static route made to the current segment

        The socket is used to receive the robot_config file"""
        network_prefix = self._router.check_static_route()

        # Check if network_prefix is not None and is a digit string
        if network_prefix and network_prefix.replace(".", "").isdigit():
            target_nano = ".".join(network_prefix.split(".")[:3]) + ".100"
            print(target_nano)
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

            self.timer = RepeatedTimer(60, self.check_and_start_SUB, self.quit_event)


class SocketManager:
    def __init__(self, teleop_chatter, quit_event):
        self.quit_event = quit_event
        self.tel_chatter_actions = teleop_chatter
        # Initialize sockets as instance variables
        self.coms_chatter = JSONPublisher(url="ipc:///byodr/coms_c.sock", topic="aav/coms/chatter")
        self.tel_chatter_socket = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=quit_event)
        self.teleop_receiver = json_collector(url="ipc:///byodr/teleop_to_coms.sock", topic=b"aav/teleop/input", event=quit_event)
        self.coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

        #  No need to call socket_manager.coms_to_pilot() in main() loop, as it's already being executed in its own thread
        self.threads = [self.tel_chatter_socket, self.teleop_receiver, threading.Thread(target=self.coms_to_pilot)]

    def coms_to_pilot(self):
        while not self.quit_event.is_set():
            self.publish_to_coms(self.teleop_receiver.get())

    def publish_to_coms(self, message):
        # Method to publish a message using coms_to_pilot_publisher
        self.coms_to_pilot_publisher.publish(message)

    def teleop_input(self):
        # Method to get data from teleop_receiver
        while not self.quit_event.is_set():
            return self.teleop_receiver.get()

    def get_teleop_chatter(self):
        while not self.quit_event.is_set():
            teleop_chatter_message = self.tel_chatter_socket.get()
            self.tel_chatter_actions.filter_robot_config(teleop_chatter_message)
            return teleop_chatter_message

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


class TeleopChatter:
    """Resolve the data incoming from Teleop chatter socket"""

    def __init__(self, _robot_config_dir, _segment_config_dir):
        self.robot_config_dir = _robot_config_dir
        self.seg_config_dir = _segment_config_dir
        self.robot_actions = RobotActions(self.robot_config_dir)

    def filter_robot_config(self, tel_data):
        """Get new robot_config from TEL chatter socket

        Args:
            tel_data (object): Full message returned from TEL chatter
        """
        # Check if tel_data is not None and then check for existence of 'robot_config'
        if tel_data and "robot_config" in tel_data.get("command", {}):
            new_robot_config = tel_data["command"]["robot_config"]
            logger.info(new_robot_config)
            self.robot_actions.driver(new_robot_config)

    def filter_watch_dog(self):
        """place holder for watchdog function"""
        pass
