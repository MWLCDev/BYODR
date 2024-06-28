#!/usr/bin/env python
from __future__ import absolute_import

import argparse
import asyncio
import configparser
import glob
import logging
import multiprocessing
import os
import signal
import threading
from concurrent.futures import ThreadPoolExecutor

from byodr.utils import Application, ApplicationExit, hash_dict
from byodr.utils.ipc import CameraThread, JSONPublisher, JSONZmqClient, json_collector
from byodr.utils.navigate import FileSystemRouteDataSource, ReloadableDataSource
from byodr.utils.option import parse_option
from byodr.utils.ssh import Router, Nano
from logbox.app import LogApplication, PackageApplication
from logbox.core import MongoLogBox, SharedState, SharedUser
from logbox.web import DataTableRequestHandler, JPEGImageRequestHandler
from pymongo import MongoClient
from six.moves.configparser import SafeConfigParser
from tornado import ioloop, web
from tornado.httpserver import HTTPServer
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from .server import *
from .tel_utils import EndpointHandlers, ThrottleController, EndpointHandlers

logger = logging.getLogger(__name__)

log_format = "%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s"

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

quit_event = multiprocessing.Event()
# A thread pool to run blocking tasks
thread_pool = ThreadPoolExecutor()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


def _load_nav_image(fname):
    image = cv2.imread(fname)
    image = cv2.resize(image, (160, 120))
    image = image.astype(np.uint8)
    return image


class TeleopApplication(Application):
    """set up configuration directory and a configuration file path

    Args:
        event: allow for thread-safe signaling between processes or threads.
    """

    def __init__(self, event, hz, config_dir=os.getcwd()):
        super(TeleopApplication, self).__init__(quit_event=event, run_hz=hz)
        self._config_dir = config_dir
        self._config_hash = -1
        # Initialize variables to None
        self._robot_config_file = None
        self._user_config_file = None
        self._router = Router()
        self._nano = Nano()

    def _config(self):
        parser = SafeConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, "*.ini"))]
        cfg = dict(parser.items("teleop")) if parser.has_section("teleop") else {}
        return cfg

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

    def get_user_config_dir(self):
        return self._user_config_file

    def get_robot_config_dir(self):
        return self._robot_config_file

    def populate_robot_config(self):
        """Add mac address, SSID, and IP for current robot in robot_config file"""
        # It is done here because vehicle service doesn't support any communication with the router (low py version 2.7)
        config = configparser.ConfigParser()
        config.read(self._robot_config_file)

        # Check how many segments are present
        segments = [s for s in config.sections() if s.startswith("segment_")]
        if len(segments) > 1:
            logger.info("Part of robot. Nothing to do.")
            return

        if len(segments) == 1:
            segment = segments[0]

            # Fetch new values
            new_values = {
                "mac.address": self._router.fetch_router_mac(),
                "wifi.name": self._router.fetch_ssid(),
                "ip.number": self._nano.get_ip_address(),
            }

            updated = False
            for key, new_value in new_values.items():
                # Get current value
                current_value = config.get(segment, key, fallback="")

                if new_value != current_value:
                    config[segment][key] = new_value
                    logger.info(f"Changed value of {key} with {new_value}")
                    updated = True

            # Write the updated configuration back to the file if there were updates
            if updated:
                with open(self._robot_config_file, "w") as configfile:
                    config.write(configfile)
            else:
                logger.info("No changes made to the robot configuration.")

    def setup(self):
        if self.active():
            self.__check_configuration_files()
            self.populate_robot_config()
            _config = self._config()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash

    def read_user_config(self):
        """
        Reads the configuration file, flattens the configuration sections and keys,
        and initializes components with specific configuration values.
        """
        config = configparser.ConfigParser()
        config.read(self.get_user_config_dir())

        # Flatten the configuration sections and keys into a single dictionary
        config_dict = {f"{section}.{option}": value for section in config.sections() for option, value in config.items(section)}

        errors = []
        # Use the flattened config dictionary as **kwargs to parse_option
        # A close implementation for how the parse_option is called in the internal_start function for each service.
        self.rut_ip = parse_option("vehicle.gps.provider.host", str, "192.168.1.1", errors, **config_dict)

        if errors:
            for error in errors:
                logger.info(f"Configuration error: {error}")

    def setup(self):
        if self.active():
            self.__check_configuration_files()
            self.read_user_config()
            _config = self._config()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash


def main():
    """
    It parses command-line arguments for configuration details and sets up various components:
      - MongoDB connection and indexing.
      - Route data source for navigation.
      - Camera threads for front and rear cameras.
      - JSON collectors for the pilot, vehicle, and inference data.
      - LogBox setup for logging.
      - Threaded applications for logging and packaging data.

    It initializes multiple threads for various components, including cameras, pilot, vehicle, inference, and logging.

    JSON publishers are set up for teleop data and chatter data.

    """
    parser = argparse.ArgumentParser(description="Teleop sockets server.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")
    parser.add_argument("--routes", type=str, default="/routes", help="Directory with the navigation routes.")
    parser.add_argument("--sessions", type=str, default="/sessions", help="Sessions directory.")
    args = parser.parse_args()

    # The mongo client is thread-safe and provides for transparent connection pooling.
    _mongo = MongoLogBox(MongoClient())
    _mongo.ensure_indexes()

    route_store = ReloadableDataSource(FileSystemRouteDataSource(directory=args.routes, fn_load_image=_load_nav_image, load_instructions=False))
    route_store.load_routes()

    camera_front = CameraThread(url="ipc:///byodr/camera_0.sock", topic=b"aav/camera/0", event=quit_event)
    camera_rear = CameraThread(url="ipc:///byodr/camera_1.sock", topic=b"aav/camera/1", event=quit_event)
    pilot = json_collector(url="ipc:///byodr/pilot.sock", topic=b"aav/pilot/output", event=quit_event, hwm=20)
    vehicle = json_collector(url="ipc:///byodr/vehicle.sock", topic=b"aav/vehicle/state", event=quit_event, hwm=20)
    inference = json_collector(url="ipc:///byodr/inference.sock", topic=b"aav/inference/state", event=quit_event, hwm=20)
    teleop_to_coms_publisher = JSONPublisher(url="ipc:///byodr/teleop_to_coms.sock", topic="aav/teleop/input")
    chatter = JSONPublisher(url="ipc:///byodr/teleop_c.sock", topic="aav/teleop/chatter")
    zm_client = JSONZmqClient(urls=["ipc:///byodr/pilot_c.sock", "ipc:///byodr/inference_c.sock", "ipc:///byodr/vehicle_c.sock", "ipc:///byodr/relay_c.sock", "ipc:///byodr/camera_c.sock"])

    logbox_user = SharedUser()
    logbox_state = SharedState(channels=(camera_front, (lambda: pilot.get()), (lambda: vehicle.get()), (lambda: inference.get())), hz=16)
    log_application = LogApplication(_mongo, logbox_user, logbox_state, event=quit_event, config_dir=args.config)
    package_application = PackageApplication(_mongo, logbox_user, event=quit_event, hz=0.100, sessions_dir=args.sessions)
    throttle_controller = ThrottleController(teleop_to_coms_publisher, route_store)
    application = TeleopApplication(event=quit_event, config_dir=args.config, hz=20)
    endpoint_handlers = EndpointHandlers(application, chatter, zm_client, route_store)
    logbox_thread = threading.Thread(target=log_application.run)
    package_thread = threading.Thread(target=package_application.run)
    threads = [camera_front, camera_rear, pilot, vehicle, inference, logbox_thread, package_thread]
    application.setup()

    if quit_event.is_set():
        return 0

    [t.start() for t in threads]

    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    asyncio.set_event_loop(asyncio.new_event_loop())

    io_loop = ioloop.IOLoop.instance()
    _conditional_exit = ApplicationExit(quit_event, lambda: io_loop.stop())
    _periodic = ioloop.PeriodicCallback(lambda: _conditional_exit(), 5e3)
    _periodic.start()

    try:
        main_app = web.Application(
            [
                # Landing page
                (r"/", DirectingUser),
                # Navigate to normal controller page
                (r"/(nc)", TemplateRenderer),
                # Navigate to user menu settings page
                (r"/(user_menu)", TemplateRenderer),
                # Navigate to Mobile controller UI
                (r"/(mc)", TemplateRenderer),
                # Getting the commands from the mobile controller (commands are sent in JSON)
                (r"/ws/send_mobile_controller_commands", MobileControllerCommands, dict(throttle_controller=throttle_controller.throttle_control)),
                # Run python script to get the SSID for the current segment
                (r"/run_get_SSID", RunGetSSIDPython),
                (r"/ws/switch_confidence", ConfidenceHandler, dict(inference_s=inference, vehicle_s=vehicle)),
                (r"/api/datalog/event/v10/table", DataTableRequestHandler, dict(mongo_box=_mongo)),
                (r"/api/datalog/event/v10/image", JPEGImageRequestHandler, dict(mongo_box=_mongo)),
                # Get the commands from the controller in normal UI
                (r"/ws/ctl", ControlServerSocket, dict(fn_control=throttle_controller.throttle_control)),
                (r"/ws/log", MessageServerSocket, dict(fn_state=(lambda: (pilot.peek(), vehicle.peek(), inference.peek())))),
                (r"/ws/cam/front", CameraMJPegSocket, dict(image_capture=(lambda: camera_front.capture()))),
                (r"/ws/cam/rear", CameraMJPegSocket, dict(image_capture=(lambda: camera_rear.capture()))),
                (r"/ws/nav", NavImageHandler, dict(fn_get_image=(lambda image_id: endpoint_handlers.get_navigation_image(image_id)))),
                # Get or save the options for the user
                (r"/teleop/user/options", ApiUserOptionsHandler, dict(user_options=(UserOptions(application.get_user_config_dir())), fn_on_save=endpoint_handlers.on_options_save)),
                (r"/teleop/system/state", JSONMethodDumpRequestHandler, dict(fn_method=endpoint_handlers.list_process_start_messages)),
                (r"/teleop/system/capabilities", JSONMethodDumpRequestHandler, dict(fn_method=endpoint_handlers.list_service_capabilities)),
                (r"/teleop/navigation/routes", JSONNavigationHandler, dict(route_store=route_store)),
                # Path to where the static files are stored (JS, CSS, images)
                (r"/(.*)", web.StaticFileHandler, {"path": os.path.join(os.path.sep, "app", "htm")}),
            ],  # Disable request logging with an empty lambda expression
            # un/comment if you want to see the requests from tornado
            log_function=lambda *args, **kwargs: None,
        )
        http_server = HTTPServer(main_app, xheaders=True)
        port_number = 8080
        http_server.bind(port_number)
        http_server.start()
        logger.info(f"Teleop web services starting on port {port_number}.")
        io_loop.start()
    except KeyboardInterrupt:
        quit_event.set()
    finally:
        _mongo.close()
        _periodic.stop()

    route_store.quit()

    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
