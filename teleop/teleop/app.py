#!/usr/bin/env python
from __future__ import absolute_import

import argparse
import asyncio
import glob
import multiprocessing
import signal
import subprocess  # to run the python script
import tornado.web
import concurrent.futures
import configparser
import user_agents  # Check in the request header if it is a phone or not


from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
from tornado import ioloop, web
from tornado.httpserver import HTTPServer
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
import tornado.ioloop
import tornado.web

from byodr.utils import Application, hash_dict, ApplicationExit
from byodr.utils.ipc import CameraThread, JSONPublisher, JSONZmqClient, json_collector
from byodr.utils.navigate import FileSystemRouteDataSource, ReloadableDataSource
from byodr.utils.ssh import Router, Cameras, Nano
from logbox.app import LogApplication, PackageApplication
from logbox.core import MongoLogBox, SharedUser, SharedState
from logbox.web import DataTableRequestHandler, JPEGImageRequestHandler
from .server import *

from htm.plot_training_sessions_map.draw_training_sessions import draw_training_sessions


# router.fetch_ip_and_mac()
# router.fetch_segment_ip
# router.get_wifi_networks()
cameras = Cameras(segment_network_prefix="192.168.1")
# router.connect_to_network("CP_Davide", "00:1E:42:2C:9F:77", "Orangebachcps1n4")
# router.delete_network("CP_Davide")
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
    def __init__(self, event, config_dir=os.getcwd()):
        """set up configuration directory and a configuration file path

        Args:
            event: allow for thread-safe signaling between processes or threads, indicating when to gracefully shut down or quit certain operations. The TeleopApplication would use this event to determine if it should stop or continue its operations.

            config_dir: specified by the command-line argument --config in the main function. Its default value is set to os.getcwd(), meaning if it's not provided externally, it'll default to the current working directory where the script is run. When provided, this directory is where the application expects to find its .ini configuration files.
        """
        super(TeleopApplication, self).__init__(quit_event=event)
        self._config_dir = config_dir
        self._user_config_file = os.path.join(self._config_dir, "config.ini")
        self._robot_config_file = os.path.join(self._config_dir, "robotConfig.ini")
        self._config_hash = -1

    def _check_configuration_files(self):
        _candidates = glob.glob(os.path.join(self._config_dir, "*.ini"))
        if len(_candidates) > 0:
            self._robot_config_file = _candidates[0]
            self._user_config_file = _candidates[1]

    def _config(self):
        parser = SafeConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, "*.ini"))]
        cfg = dict(parser.items("teleop")) if parser.has_section("teleop") else {}
        return cfg

    def get_user_config_file(self):
        return self._user_config_file

    def get_robot_config_file(self):
        return self._robot_config_file

    def __get_nano_IP(self):
        nano = Nano()
        data = nano.get_ip_address()
        self.router = Router(data)

    def setup(self):
        if self.active():
            self._check_configuration_files()
            self.__get_nano_IP()
            _config = self._config()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash


def run_python_script(script_name):
    import subprocess

    result = subprocess.check_output(["python3", script_name], universal_newlines=True)
    result_list = result.strip().split("\n")
    return result_list


class RunDrawMapPython(tornado.web.RequestHandler):
    """Run the python script file and get the response of the sessions date and the Create .HTML file for them to be sent to JS function"""

    async def get(self):
        script_name = "./htm/plot_training_sessions_map/draw_training_sessions.py"
        with concurrent.futures.ProcessPoolExecutor() as executor:
            future = executor.submit(run_python_script, script_name)
            # Use the `await` keyword to asynchronously wait for the result.
            result_list = await tornado.ioloop.IOLoop.current().run_in_executor(
                None, future.result
            )

            # Print the list before sending it to the JavaScript function.
            logger.info("Python script result: ", result_list)

            # Convert the list to a string representation to send it back to the client.
            result_str = "\n".join(result_list)
            # logger.info(f"That is coming from the JSON list {result_str}")
            self.write(result_str)
            self.finish()


class GetSegmentSSID(tornado.web.RequestHandler):
    """Run a python script to get the SSID of current robot"""

    async def get(self):
        try:
            # Use the IOLoop to run fetch_ssid in a thread
            loop = tornado.ioloop.IOLoop.current()

            config = configparser.ConfigParser()
            config.read("/config/config.ini")
            front_camera_ip = config["camera"]["front.camera.ip"]
            parts = front_camera_ip.split(".")
            network_prefix = ".".join(parts[:3])
            router_IP = f"{network_prefix}.1"
            # name of python function to run, ip of the router, ip of SSH, username, password, command to get the SSID
            ssid = await loop.run_in_executor(
                None,
                router.fetch_ssid,
            )

            logger.info(f"SSID of current robot: {ssid}")
            self.write(ssid)
        except Exception as e:
            logger.error(f"Error fetching SSID of current robot: {e}")
            logger.error(traceback.format_exc())  # This will pri
            self.set_status(500)
            self.write("Error fetching SSID of current robot.")
        self.finish()


class DirectingUser(tornado.web.RequestHandler):
    """Directing the user based on their used device"""

    def get(self):
        user_agent_str = self.request.headers.get("User-Agent")
        user_agent = user_agents.parse(user_agent_str)

        if user_agent.is_mobile:
            # if user is on mobile, redirect to the mobile page
            logger.info(
                "User is operating through mobile phone. Redirecting to the mobile UI"
            )
            self.redirect("/mobile_controller_ui")
        else:
            # else redirect to normal control page
            self.redirect("/normalcontrol")


class TemplateRenderer(tornado.web.RequestHandler):
    _TEMPLATES = {
        "normalcontrol": "index.html",
        "user_menu": "user_menu.html",
        "user_admin": "user_admin.html",
        "mobile_controller_ui": "mobile_controller_ui.html",
        "testFeature": "testFeature.html",
    }

    def get(self, page_name):
        template_name = self._TEMPLATES.get(page_name)
        if template_name:
            self.render(f"../htm/templates/{template_name}")
        else:
            self.set_status(404)
            self.write("Page not found.")


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
    parser.add_argument(
        "--config", type=str, default="/config", help="Config directory path."
    )
    parser.add_argument(
        "--routes",
        type=str,
        default="/routes",
        help="Directory with the navigation routes.",
    )
    parser.add_argument(
        "--sessions", type=str, default="/sessions", help="Sessions directory."
    )
    args = parser.parse_args()

    # The mongo client is thread-safe and provides for transparent connection pooling.
    _mongo = MongoLogBox(MongoClient())
    _mongo.ensure_indexes()

    route_store = ReloadableDataSource(
        FileSystemRouteDataSource(
            directory=args.routes,
            fn_load_image=_load_nav_image,
            load_instructions=False,
        )
    )
    route_store.load_routes()

    application = TeleopApplication(event=quit_event, config_dir=args.config)
    application.setup()

    camera_front = CameraThread(
        url="ipc:///byodr/camera_0.sock", topic=b"aav/camera/0", event=quit_event
    )
    camera_rear = CameraThread(
        url="ipc:///byodr/camera_1.sock", topic=b"aav/camera/1", event=quit_event
    )
    pilot = json_collector(
        url="ipc:///byodr/pilot.sock",
        topic=b"aav/pilot/output",
        event=quit_event,
        hwm=20,
    )
    vehicle = json_collector(
        url="ipc:///byodr/vehicle.sock",
        topic=b"aav/vehicle/state",
        event=quit_event,
        hwm=20,
    )
    inference = json_collector(
        url="ipc:///byodr/inference.sock",
        topic=b"aav/inference/state",
        event=quit_event,
        hwm=20,
    )

    logbox_user = SharedUser()
    logbox_state = SharedState(
        channels=(
            camera_front,
            (lambda: pilot.get()),
            (lambda: vehicle.get()),
            (lambda: inference.get()),
        ),
        hz=16,
    )
    log_application = LogApplication(
        _mongo, logbox_user, logbox_state, event=quit_event, config_dir=args.config
    )
    package_application = PackageApplication(
        _mongo, logbox_user, event=quit_event, hz=0.100, sessions_dir=args.sessions
    )

    logbox_thread = threading.Thread(target=log_application.run)
    package_thread = threading.Thread(target=package_application.run)

    threads = [
        camera_front,
        camera_rear,
        pilot,
        vehicle,
        inference,
        logbox_thread,
        package_thread,
    ]
    if quit_event.is_set():
        return 0

    [t.start() for t in threads]

    teleop_publisher = JSONPublisher(
        url="ipc:///byodr/teleop.sock", topic="aav/teleop/input"
    )
    # external_publisher = JSONPublisher(url='ipc:///byodr/external.sock', topic='aav/external/input')
    chatter = JSONPublisher(
        url="ipc:///byodr/teleop_c.sock", topic="aav/teleop/chatter"
    )
    zm_client = JSONZmqClient(
        urls=[
            "ipc:///byodr/pilot_c.sock",
            "ipc:///byodr/inference_c.sock",
            "ipc:///byodr/vehicle_c.sock",
            "ipc:///byodr/relay_c.sock",
            "ipc:///byodr/camera_c.sock",
        ]
    )

    def on_options_save():
        chatter.publish(dict(time=timestamp(), command="restart"))
        application.setup()

    def list_process_start_messages():
        return zm_client.call(dict(request="system/startup/list"))

    def list_service_capabilities():
        return zm_client.call(dict(request="system/service/capabilities"))

    def get_navigation_image(image_id):
        return route_store.get_image(image_id)

    def teleop_publish(cmd):
        # We are the authority on route state.
        cmd["navigator"] = dict(route=route_store.get_selected_route())
        teleop_publisher.publish(cmd)

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
                (r"/(normalcontrol)", TemplateRenderer),
                # Navigate to user menu settings page
                (r"/(user_menu)", TemplateRenderer),
                # Navigate to admin section in user menu
                (r"/(user_admin)", TemplateRenderer),
                # Navigate to Mobile controller UI
                (r"/(mobile_controller_ui)", TemplateRenderer),
                # Navigate to a testing page
                (r"/(testFeature)", TemplateRenderer),
                # Run python script to get list of maps
                (
                    r"/run_draw_map_python",
                    RunDrawMapPython,
                ),
                (
                    # Getting the commands from the mobile controller (commands are sent in JSON)
                    r"/ws/send_mobile_controller_commands",
                    MobileControllerCommands,
                    dict(fn_control=teleop_publish),
                ),
                # Run python script to get the SSID for the current segment
                (r"/run_get_SSID", GetSegmentSSID),
                (
                    r"/api/datalog/event/v10/table",
                    DataTableRequestHandler,
                    dict(mongo_box=_mongo),
                ),
                (
                    r"/api/datalog/event/v10/image",
                    JPEGImageRequestHandler,
                    dict(mongo_box=_mongo),
                ),  # Get the commands from the controller in normal UI
                (r"/ws/ctl", ControlServerSocket, dict(fn_control=teleop_publish)),
                (
                    r"/ws/log",
                    MessageServerSocket,
                    dict(
                        fn_state=(
                            lambda: (pilot.peek(), vehicle.peek(), inference.peek())
                        )
                    ),
                ),
                (
                    r"/ws/cam/front",
                    CameraMJPegSocket,
                    dict(image_capture=(lambda: camera_front.capture())),
                ),
                (
                    r"/ws/cam/rear",
                    CameraMJPegSocket,
                    dict(image_capture=(lambda: camera_rear.capture())),
                ),
                (
                    r"/ws/nav",
                    NavImageHandler,
                    dict(
                        fn_get_image=(lambda image_id: get_navigation_image(image_id))
                    ),
                ),
                (
                    # Get or save the options for the user
                    r"/teleop/user/options",
                    ApiUserOptionsHandler,
                    dict(
                        user_options=(
                            ConfigManager(application.get_user_config_file())
                        ),
                        fn_on_save=on_options_save,
                    ),
                ),
                (
                    # Get or save the options for the robot
                    r"/teleop/robot/options",
                    ApiUserOptionsHandler,
                    dict(
                        user_options=(
                            ConfigManager(application.get_robot_config_file())
                        ),
                        fn_on_save=on_options_save,
                    ),
                ),
                (r"/ssh/router", RouterSSHHandler),
                (
                    r"/teleop/system/state",
                    JSONMethodDumpRequestHandler,
                    dict(fn_method=list_process_start_messages),
                ),
                (
                    r"/teleop/system/capabilities",
                    JSONMethodDumpRequestHandler,
                    dict(fn_method=list_service_capabilities),
                ),
                (
                    r"/teleop/navigation/routes",
                    JSONNavigationHandler,
                    dict(route_store=route_store),
                ),
                (
                    # Path to where the static files are stored (JS,CSS, images)
                    r"/(.*)",
                    web.StaticFileHandler,
                    {"path": os.path.join(os.path.sep, "app", "htm")},
                ),
            ],  # Disable request logging with an empty lambda expression
            # Always restart after you change path of folder/file
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
