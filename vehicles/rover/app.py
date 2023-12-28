import argparse
import collections
import glob
import logging
import os
import shutil
import subprocess
import re

from ConfigParser import SafeConfigParser

from byodr.utils import Application, PeriodicCallTrace
from byodr.utils import timestamp, Configurable
from byodr.utils.ipc import (
    JSONPublisher,
    ImagePublisher,
    LocalIPCServer,
    json_collector,
    ReceiverThread,
)
from byodr.utils.location import GeoTracker
from byodr.utils.option import parse_option, hash_dict
from core import GpsPollerThread, PTZCamera, ConfigurableImageGstSource

logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s"


class RasRemoteError(IOError):
    def __init__(self, timeout):
        self.timeout = timeout


class RasSpeedOdometer(object):
    def __init__(self, master_uri, speed_factor):
        self._ras_uri = master_uri
        # The speed factor must be in m/s.
        self._motor_effort_speed_factor = speed_factor
        self._values = collections.deque(maxlen=1)
        self._receiver = None
        # Initialize the queue with the startup time.
        self._values.append((0, timestamp()))

    def _on_receive(self, msg):
        # Some robots do not have a sensor for speed.
        # If velocity is not part of the ras message try to come up with a proxy for speed.
        if "velocity" in msg.keys():
            value = float(msg.get("velocity"))
        else:
            # The motor effort is calculated as the motor scale * the actual throttle.
            # In case the robot's maximum speed is hardware limited to 10km/h and the motor scale is 4
            # the speed factor is set to 10 / 4 / 3.6.
            value = float(msg.get("motor_effort")) * self._motor_effort_speed_factor
        self._values.append((value, timestamp()))

    def get(self):
        value, ts = self._values[-1]
        _duration = (timestamp() - ts) * 1e-3  # convert to milliseconds.
        # Half a second is already an eternity.
        if _duration > 500:
            raise RasRemoteError(_duration)
        return value

    def start(self):
        # The receiver thread is not restartable.
        self._receiver = ReceiverThread(url=("{}:5555".format(self._ras_uri)), topic=b"ras/drive/status")
        self._receiver.add_listener(self._on_receive)
        self._receiver.start()

    def quit(self):
        if self._receiver is not None:
            self._receiver.quit()


class Platform(Configurable):
    def __init__(self):
        super(Platform, self).__init__()
        self._odometer = None
        self._odometer_config = None
        self._gps = None
        self._geo = GeoTracker()

    def _track(self):
        latitude, longitude = (None, None) if self._gps is None else (self._gps.get_latitude(), self._gps.get_longitude())
        position = None if None in (latitude, longitude) else (latitude, longitude)
        return self._geo.track(position)

    def _start_odometer(self):
        _master_uri, _speed_factor = self._odometer_config
        self._odometer = RasSpeedOdometer(_master_uri, _speed_factor)
        self._odometer.start()

    def _quit_odometer(self):
        if self._odometer is not None:
            self._odometer.quit()

    def state(self):
        with self._lock:
            y_vel, trust_velocity = 0, 0
            latitude, longitude, bearing = self._track()
            if self._odometer is not None:
                try:
                    y_vel, trust_velocity = self._odometer.get(), 1
                except RasRemoteError as rre:
                    # After 5 seconds do a hard reboot of the remote connection.
                    if rre.timeout > 5000:
                        logger.info("Hard odometer reboot at {} ms timeout.".format(rre.timeout))
                        self._quit_odometer()
                        self._start_odometer()
            return dict(
                latitude_geo=latitude,
                longitude_geo=longitude,
                heading=bearing,
                velocity=y_vel,
                trust_velocity=trust_velocity,
                time=timestamp(),
            )

    def internal_quit(self, restarting=False):
        self._quit_odometer()
        if self._gps is not None:
            self._gps.quit()

    def internal_start(self, **kwargs):
        errors = []
        _master_uri = parse_option("ras.master.uri", str, "192.168.1.32", errors, **kwargs)
        _master_uri = "tcp://{}".format(_master_uri)
        _speed_factor = parse_option("ras.non.sensor.speed.factor", float, 0.50, errors, **kwargs)
        self._odometer_config = (_master_uri, _speed_factor)
        self._start_odometer()
        _gps_host = parse_option("gps.provider.host", str, "192.168.1.1", errors, **kwargs)
        _gps_port = parse_option("gps.provider.port", str, "502", errors, **kwargs)
        self._gps = GpsPollerThread(_gps_host, _gps_port)
        self._gps.start()
        return errors


class RoverHandler(Configurable):
    def __init__(self, config_dir):
        super(RoverHandler, self).__init__()
        self._config_dir = config_dir
        self._platform = Platform()
        self._process_frequency = 10
        self._patience_micro = 100.0
        self._gst_calltrace = PeriodicCallTrace(seconds=10.0)
        self._gst_sources = []
        self._ptz_cameras = []

    def get_process_frequency(self):
        return self._process_frequency

    def get_patience_micro(self):
        return self._patience_micro

    def is_reconfigured(self, **kwargs):
        return True

    def internal_quit(self, restarting=False):
        if not restarting:
            self._platform.quit()
            map(lambda x: x.quit(), self._ptz_cameras)
            map(lambda x: x.quit(), self._gst_sources)

    def internal_start(self, **kwargs):
        errors = []
        self._process_frequency = parse_option("clock.hz", int, 80, errors, **kwargs)
        self._patience_micro = parse_option("patience.ms", int, 100, errors, **kwargs) * 1000.0
        self._platform.restart(**kwargs)
        errors.extend(self._platform.get_errors())
        if not self._gst_sources:
            front_camera = ImagePublisher(url="ipc:///byodr/camera_0.sock", topic="aav/camera/0")
            rear_camera = ImagePublisher(url="ipc:///byodr/camera_1.sock", topic="aav/camera/1")
            self._gst_sources.append(ConfigurableImageGstSource("front", image_publisher=front_camera))
            self._gst_sources.append(ConfigurableImageGstSource("rear", image_publisher=rear_camera))
        if not self._ptz_cameras:
            self._ptz_cameras.append(PTZCamera("front", self._config_dir))
            self._ptz_cameras.append(PTZCamera("rear", self._config_dir))
        for item in self._gst_sources + self._ptz_cameras:
            item.restart(**kwargs)
            errors.extend(item.get_errors())
        return errors

    def get_video_capabilities(self):
        # The video dimensions are determined by the websocket services.
        front, rear = self._gst_sources
        return {"front": {"ptz": front.get_ptz()}, "rear": {"ptz": rear.get_ptz()}}

    def _check_gst_sources(self):
        self._gst_calltrace(lambda: list(map(lambda x: x.check(), self._gst_sources)))

    def _cycle_ptz_cameras(self, c_pilot, c_teleop):
        """Moves the camera based on the command from teleop

        Args:
            c_pilot (JSON): Command from pilot
            c_teleop (JSON): command to pilot
        """
        # The front camera ptz function is enabled for teleop direct driving only.
        # Set the front camera to the home position anytime the autopilot is switched on.
        if self._ptz_cameras and c_teleop is not None:
            c_camera = c_teleop.get("camera_id", -1)
            # Lower camera is 0 and upper is 1
            _north_pressed = bool(c_teleop.get("button_y", 0))
            _is_teleop = c_pilot is not None and c_pilot.get("driver") == "driver_mode.teleop.direct"
            if _north_pressed:
                # North =  Triangle in PS4 controller
                self._ptz_cameras[0].add({"goto_home": 1})
            elif c_camera in (0, 1) and (c_camera == 1 or _is_teleop):
                # Ignore the pan value on the front camera unless explicitly specified with a button press.
                # Hold Square then press X to set the current position for PT to be home position
                _south_pressed = bool(c_teleop.get("button_a", 0))  # X
                _west_pressed = bool(c_teleop.get("button_x", 0))  # Square
                _read_pan = _west_pressed or c_camera > 0
                tilt_value = c_teleop.get("tilt", 0)
                pan_value = c_teleop.get("pan", 0) if _read_pan else 0
                _set_home = _west_pressed and abs(tilt_value) < 1e-2 and abs(pan_value) < 1e-2
                command = {
                    "pan": pan_value,
                    "tilt": tilt_value,
                    "set_home": 1 if _set_home else 0,
                    "goto_home": 1 if _south_pressed else 0,
                }
                self._ptz_cameras[c_camera].add(command)

    def step(self, c_pilot, c_teleop):
        self._cycle_ptz_cameras(c_pilot, c_teleop)
        self._check_gst_sources()
        return self._platform.state()


class ConfigFiles:
    def __init__(self, config_dir):
        self._config_dir = config_dir
        self.__set_parsers()

    def __set_parsers(self):
        self.robot_config_dir = os.path.join(self._config_dir, "robot_config.ini")
        self.segment_config_dir = os.path.join(self._config_dir, "config.ini")
        self.robot_config_parser = SafeConfigParser()
        self.segment_config_parser = SafeConfigParser()
        self.robot_config_parser.read(self.robot_config_dir)
        self.segment_config_parser.read(self.segment_config_dir)

    def check_configuration_files(self):
        """Checks if configuration file for segment and robot exist, if not, then create them from the template"""
        # FOR DEBUGGING
        # _candidates = glob.glob(os.path.join(self._config_dir, "*.ini"))
        # print(_candidates)
        required_files = ["config.ini", "robot_config.ini"]
        template_files = {
            "config.ini": "config.template",
            "robot_config.ini": "robot_config.template",
        }
        # Local mode => /mnt/data/docker/volumes/1_volume_byodr_config/_data/robot_config.ini
        for file in required_files:
            file_path = os.path.join(self._config_dir, file)
            if not os.path.exists(file_path):
                template_file = template_files[file]
                shutil.copyfile(template_file, file_path)
                logger.info("Created {} from template.".format(file))

            # Verify and add missing keys
            self._verify_and_add_missing_keys(file_path, template_files[file])

    def _verify_and_add_missing_keys(self, ini_file, template_file):
        config = SafeConfigParser()
        template_config = SafeConfigParser()

        config.read(ini_file)
        template_config.read(template_file)

        # Loop through each section and key in the template
        for section in template_config.sections():
            if not config.has_section(section):
                config.add_section(section)
            for key, value in template_config.items(section):
                if not config.has_option(section, key):
                    config.set(section, key, value)
                    logger.info("Added missing key '{}' in section '[{}]' to {}".format(key, section, ini_file))

        # Write changes to the ini file
        with open(ini_file, "w") as configfile:
            config.write(configfile)

    def update_robot_config(self):
        """Check and update the IP address in robot_config.ini."""
        # Count the number of 'segment_' sections
        segment_count = sum(1 for section in self.robot_config_parser.sections() if section.startswith("segment_"))
        print(segment_count)
        if segment_count != 1:
            print("This segment is part of a robot. No changes to be made in robot_config.ini")
            return

        ip_changed = self.__update_ip_address()

        if not ip_changed:
            logger.info("No need to change IP in robot_config.ini")
        else:
            logger.info("Updated robot_config.ini")

    def __update_ip_address(self):
        """Update the IP address in robot_config.ini if necessary."""
        config_ip_number = self.robot_config_parser.get("segment_1", "ip.number")
        ip_addresses = (
            subprocess.check_output(
                "hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'",
                shell=True,
            )
            .decode()
            .strip()
        )
        if config_ip_number != ip_addresses:
            self.robot_config_parser.set("segment_1", "ip.number", ip_addresses)
            with open(self.robot_config_dir, "w") as config_file:
                self.robot_config_parser.write(config_file)
            logger.info("Changed IP in robot_config.ini to {}".format(ip_addresses))
            return True
        return False

    # def __update_mac_address(self):
    #     """Update the MAC address in robot_config.ini if necessary."""
    #     config_mac_address = self.segment_config_parser.get("segment_1", "mac.address")
    #     router_mac_address = self._segment_router.fetch_router_mac()
    #     if config_mac_address != router_mac_address:
    #         self.parser.set("segment_1", "mac.address", router_mac_address)
    #         with open(self.robot_config_path, "w") as config_file:
    #             self.parser.write(config_file)
    #         logger.info("Changed MAC address in robot_config.ini to {}".format(router_mac_address))
    #         return True
    #     return False

    def change_segment_config(self):
        """Change the ips in all the config files the segment is using them.
        It will count on the ip of the nano"""
        # Get the local IP address's third octet
        ip_address = subprocess.check_output("hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'", shell=True).decode().strip().split()[0]
        third_octet_new = ip_address.split(".")[2]

        _candidates = glob.glob(os.path.join(self._config_dir, "config.ini"))

        # Regular expression to match IP addresses
        ip_regex = re.compile(r"(\d+\.\d+\.)(\d+)(\.\d+)")

        for file in _candidates:
            with open(file, "r") as f:
                content = f.readlines()

            updated_content = []
            changes_made = []
            changes_made_in_file = False  # Flag to track changes in the current file

            for line in content:
                match = ip_regex.search(line)
                if match:
                    third_octet_old = match.group(2)
                    if third_octet_old != third_octet_new:
                        # Replace the third octet
                        new_line = ip_regex.sub(r"\g<1>" + third_octet_new + r"\g<3>", line)
                        updated_content.append(new_line)
                        changes_made.append((third_octet_old, third_octet_new))
                        changes_made_in_file = True

                        continue
                updated_content.append(line)

            # Write changes back to the file
            with open(file, "w") as f:
                f.writelines(updated_content)

            # Print changes made
            if changes_made_in_file:
                logger.info("Updated {} with new ip address".format(file))
            else:
                logger.info("No changes needed for {}.".format(file))


class RoverApplication(Application):
    def __init__(self, handler=None, config_dir=os.getcwd()):
        super(RoverApplication, self).__init__()
        self._config_dir = config_dir
        self._handler = RoverHandler(config_dir=self._config_dir) if handler is None else handler
        self._config_hash = -1
        self.state_publisher = None
        self.ipc_server = None
        self.pilot = None
        self.teleop = None
        self.ipc_chatter = None
        self._config_files_class = ConfigFiles(self._config_dir)

    def _config(self):
        parser = SafeConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, "*.ini"))]
        cfg = dict(parser.items("vehicle")) if parser.has_section("vehicle") else {}
        cfg.update(dict(parser.items("camera")) if parser.has_section("camera") else {})
        return cfg

    def _capabilities(self):
        return {"vehicle": "rover1", "video": self._handler.get_video_capabilities()}

    def setup(self):
        if self.active():
            _config = self._config()
            _hash = hash_dict(**_config)
            if _hash != self._config_hash:
                self._config_hash = _hash
                self._config_files_class.check_configuration_files()
                self._config_files_class.change_segment_config()
                self._config_files_class.update_robot_config()
                _config = self._config()
                _restarted = self._handler.restart(**_config)
                if _restarted:
                    self.ipc_server.register_start(self._handler.get_errors(), self._capabilities())
                    _frequency = self._handler.get_process_frequency()
                    self.set_hz(_frequency)
                    self.logger.info("Processing at {} Hz.".format(_frequency))

    def finish(self):
        self._handler.quit()

    def step(self):
        rover, pilot, teleop, publisher = (
            self._handler,
            self.pilot,
            self.teleop,
            self.state_publisher,
        )
        c_pilot = self._latest_or_none(pilot, patience=rover.get_patience_micro())
        c_teleop = self._latest_or_none(teleop, patience=rover.get_patience_micro())
        _state = rover.step(c_pilot, c_teleop)
        publisher.publish(_state)
        chat = self.ipc_chatter()
        if chat and chat.get("command") == "restart":
            self.setup()


def main():
    parser = argparse.ArgumentParser(description="Rover main.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")
    args = parser.parse_args()

    application = RoverApplication(config_dir=args.config)
    quit_event = application.quit_event

    pilot = json_collector(url="ipc:///byodr/pilot.sock", topic=b"aav/pilot/output", event=quit_event)
    teleop = json_collector(url="ipc:///byodr/teleop.sock", topic=b"aav/teleop/input", event=quit_event)
    ipc_chatter = json_collector(
        url="ipc:///byodr/teleop_c.sock",
        topic=b"aav/teleop/chatter",
        pop=True,
        event=quit_event,
    )

    application.state_publisher = JSONPublisher(url="ipc:///byodr/vehicle.sock", topic="aav/vehicle/state")
    application.ipc_server = LocalIPCServer(url="ipc:///byodr/vehicle_c.sock", name="platform", event=quit_event)
    application.pilot = lambda: pilot.get()
    application.teleop = lambda: teleop.get()
    application.ipc_chatter = lambda: ipc_chatter.get()

    threads = [pilot, teleop, ipc_chatter, application.ipc_server]
    if quit_event.is_set():
        return 0

    [t.start() for t in threads]
    application.run()

    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
