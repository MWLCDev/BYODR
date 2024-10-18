#!/usr/bin/env python
from __future__ import absolute_import

import argparse
import asyncio
import logging
import multiprocessing
import os
import shutil
import signal
import threading
import time
import re

from configparser import ConfigParser
from BYODR_utils.PI_specific.utilities import RaspberryPi

from tornado import web, ioloop
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from BYODR_utils.common import Application
from BYODR_utils.common.option import parse_option
from BYODR_utils.common.video import create_video_source
from BYODR_utils.common.websocket import HttpLivePlayerVideoSocket, JMuxerVideoStreamSocket

# Setup logging
log_format = "%(levelname)s: %(asctime)s %(filename)s:%(lineno)d " "%(funcName)s %(threadName)s %(message)s"
logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global event to signal quitting
quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


# Setup signal handlers
signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

# GStreamer commands
GSTREAMER_COMMANDS = {
    "h264/rtsp": (
        "rtspsrc location=rtsp://{user}:{password}@{ip}:{port}{path} latency=0 "
        "drop-on-latency=true do-retransmission=false ! "
        "queue ! rtph264depay ! h264parse ! queue ! "
        "video/x-h264,stream-format=byte-stream ! queue ! appsink"
    ),
    "raw/usb/h264/udp": (
        "v4l2src device={uri} ! video/x-raw,width={src_width},height={src_height} ! "
        "videoflip method={video_flip} ! tee name=t "
        "t. ! queue ! videoconvert ! videoscale ! "
        "video/x-raw,width={udp_width},height={udp_height} ! queue ! "
        "v4l2h264enc extra-controls=encode,frame_level_rate_control_enable=1,h264_i_frame_period=50 ! queue ! "
        "video/x-h264,profile=baseline ! rtph264pay ! "
        "udpsink host={udp_host} port={udp_port} sync=false async=false "
        "t. ! queue ! videoconvert ! videoscale ! "
        "video/x-raw,width={out_width},height={out_height} ! queue ! "
        "v4l2h264enc extra-controls=encode,frame_level_rate_control_enable=1,h264_i_frame_period=50 ! queue ! "
        "video/x-h264,profile=baseline,stream-format=byte-stream ! queue ! appsink"
    ),
}


class CameraConfigFile:
    """Handles configuration file parsing and updating."""

    def __init__(self, config_file):
        self.config_file = config_file
        self.parser = ConfigParser()
        self.kwargs = {}
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file) and os.path.isfile(self.config_file):
            self.parser.read(self.config_file)
            self.kwargs = dict(self.parser.items("camera"))
            self._update_ip_addresses()
        else:
            self._create_default_config()
            # If it created a new camera config file, update the IPs inside to be dynamic
            self._update_ip_addresses()
            self.parser.read(self.config_file)
            self.kwargs = dict(self.parser.items("camera"))

    def _update_ip_addresses(self):
        """Update IP addresses in the config file to match the local IP's third octet."""
        try:
            ip_address = RaspberryPi.get_ip_address()
            third_octet_new = ip_address.split(".")[2]
            ip_regex = re.compile(r"(\d+\.\d+\.)(\d+)(\.\d+)")
            with open(self.config_file, "r") as f:
                content = f.readlines()

            updated_content = []
            changes_made = False

            for line in content:
                match = ip_regex.search(line)
                if match:
                    third_octet_old = match.group(2)
                    if third_octet_old != third_octet_new:
                        new_line = ip_regex.sub(r"\g<1>" + third_octet_new + r"\g<3>", line)
                        updated_content.append(new_line)
                        changes_made = True
                        continue
                updated_content.append(line)

            if changes_made:
                with open(self.config_file, "w") as f:
                    f.writelines(updated_content)
                logger.info(f"Updated {self.config_file} with new IP address third octet {third_octet_new}")
        except Exception as e:
            logger.error(f"Error updating IP addresses in config file: {e}")

    def _create_default_config(self):
        default_template = "/app/stream/camera.template"
        if os.path.exists(default_template):
            shutil.copyfile(default_template, self.config_file)
            logger.info(f"Created a new camera configuration file from template at {self.config_file}")
        else:
            logger.error(f"Default config template {default_template} not found.")

    def get_option(self, section, option, default=None, option_type=str):
        return parse_option(f"{section}.{option}", option_type, default, **self.kwargs)


class CameraStream:
    """Handles the creation of the camera stream based on configuration."""

    def __init__(self, config):
        self.config = config
        self.name = os.path.basename(os.path.splitext(config.config_file)[0])
        self.stream_type = self.config.get_option("camera", "type")
        self.command = None
        self.socket_ref = None
        self.video_stream = None

        self._validate_stream_type()
        self._create_stream()

    def _validate_stream_type(self):
        if self.stream_type not in GSTREAMER_COMMANDS:
            raise ValueError(f"Unrecognized camera type '{self.stream_type}'.")

    def _create_stream(self):
        try:
            if self.stream_type == "h264/rtsp":
                self._create_rtsp_stream()
            elif self.stream_type == "raw/usb/h264/udp":
                self._create_usb_udp_stream()
            else:
                raise ValueError(f"Unsupported stream type '{self.stream_type}'.")
        except Exception as e:
            logger.error(f"Error creating stream: {e}")
            raise

    def _create_rtsp_stream(self):
        out_width, out_height = self._parse_resolution(self.config.get_option("camera", "output.shape", "640x480"))
        config = {
            "ip": self.config.get_option("camera", "ip", "192.168.1.64"),
            "port": self.config.get_option("camera", "port", 554, int),
            "user": self.config.get_option("camera", "user", "user1"),
            "password": self.config.get_option("camera", "password", "HaikuPlot876"),
            "path": self.config.get_option("camera", "path", "/Streaming/Channels/103"),
        }
        self.command = GSTREAMER_COMMANDS[self.stream_type].format(**config)
        self.socket_ref = self.config.get_option("camera", "output.class", "http-live")
        location = f"rtsp://{config['user']}:{config['password']}@{config['ip']}:" f"{config['port']}{config['path']}"
        logger.info(f"Socket '{self.name}' location={location}")
        self.video_stream = create_video_source(self.name, shape=(out_height, out_width, 3), command=self.command)

    def _create_usb_udp_stream(self):
        src_width, src_height = self._parse_resolution(self.config.get_option("camera", "source.shape", "640x480"))
        udp_width, udp_height = self._parse_resolution(self.config.get_option("camera", "udp.shape", "320x240"))
        out_width, out_height = self._parse_resolution(self.config.get_option("camera", "output.shape", "480x320"))
        config = {
            "uri": self.config.get_option("camera", "uri", "/dev/video0"),
            "src_width": src_width,
            "src_height": src_height,
            "video_flip": self.config.get_option("camera", "flip.method", "none"),
            "udp_width": udp_width,
            "udp_height": udp_height,
            "udp_bitrate": self.config.get_option("camera", "udp.bitrate", 1024000, int),
            "udp_host": self.config.get_option("camera", "udp.host", "192.168.1.100"),
            "udp_port": self.config.get_option("camera", "udp.port", 5000, int),
            "out_width": out_width,
            "out_height": out_height,
            "out_bitrate": self.config.get_option("camera", "output.bitrate", 1024000, int),
        }
        self.command = GSTREAMER_COMMANDS[self.stream_type].format(**config)
        self.socket_ref = self.config.get_option("camera", "output.class", "http-live")
        self.video_stream = create_video_source(self.name, shape=(out_height, out_width, 3), command=self.command)

    @staticmethod
    def _parse_resolution(resolution_str):
        try:
            width, height = [int(x) for x in resolution_str.split("x")]
            return width, height
        except ValueError:
            raise ValueError(f"Invalid resolution format: {resolution_str}")


class CameraApplication(Application):
    """Runs the camera application loop."""

    def __init__(self, config_file, port, event):
        super().__init__(quit_event=event, run_hz=2)
        self.config_file = config_file
        self.port = port
        self.camera_stream = None
        self.io_loop = None
        self.server_thread = None

    def setup(self):
        try:
            camera_config = CameraConfigFile(self.config_file)

            self.camera_stream = CameraStream(camera_config)
            # Setup the IO loop and web application
            self._setup_web_server()
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            self.quit_event.set()

    def _setup_web_server(self):
        """Sets up the web server for the camera stream."""
        # Create a new event loop directly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.io_loop = ioloop.IOLoop.current()
        socket_class = HttpLivePlayerVideoSocket if self.camera_stream.socket_ref == "http-live" else JMuxerVideoStreamSocket
        web_app = web.Application(
            [
                (
                    r"/",
                    socket_class,
                    dict(video_source=self.camera_stream.video_stream, io_loop=self.io_loop),
                )
            ]
        )
        rear_server = web.HTTPServer(web_app, xheaders=True)
        rear_server.bind(self.port)
        rear_server.start()
        logger.info(f"Web service started on port {self.port}.")

        # Run the IO loop in a separate thread
        self.server_thread = threading.Thread(target=self.io_loop.start)
        self.server_thread.start()

    def step(self):
        try:
            if self.camera_stream and self.camera_stream.video_stream:
                self.camera_stream.video_stream.check()
        except Exception as e:
            logger.error(f"Error in CameraApplication step: {e}")
            self.quit_event.set()

    def teardown(self):
        if self.io_loop and not self.io_loop.is_closed():
            self.io_loop.add_callback(self.io_loop.stop)
            self.server_thread.join()
            logger.info("Web server stopped.")


def main():
    """Main function to parse arguments and start the application."""
    parser = argparse.ArgumentParser(description="Camera web-socket server.")
    parser.add_argument("--config", type=str, default="/config/stream.ini", help="Configuration file.")
    parser.add_argument("--port", type=int, default=9101, help="Socket port.")

    args = parser.parse_args()
    application = CameraApplication(args.config, args.port, quit_event)

    try:
        if quit_event.is_set():
            return 0
        application.run()
    finally:
        application.teardown()

    while not quit_event.is_set():
        time.sleep(1)


if __name__ == "__main__":
    main()
