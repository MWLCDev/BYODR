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
import subprocess
import re
import glob

from configparser import ConfigParser as SafeConfigParser

from tornado import web, ioloop
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from byodr.utils import Application
from byodr.utils.option import parse_option
from byodr.utils.video import create_video_source
from byodr.utils.websocket import HttpLivePlayerVideoSocket, JMuxerVideoStreamSocket

logger = logging.getLogger(__name__)

log_format = "%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s"

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


class CameraApplication(Application):
    def __init__(self, stream, event):
        super(CameraApplication, self).__init__(quit_event=event, run_hz=2)
        self._stream = stream

    def setup(self):
        pass

    def step(self):
        self._stream.check()


gst_commands = {
    "h264/rtsp": "rtspsrc location=rtsp://{user}:{password}@{ip}:{port}{path} latency=0 drop-on-latency=true do-retransmission=false ! "
    'queue ! rtph264depay ! h264parse ! queue ! video/x-h264,stream-format="byte-stream" ! queue ! appsink',
    "raw/usb/h264/udp": "v4l2src device={uri} ! video/x-raw,width={src_width},height={src_height} ! videoflip method={video_flip} ! tee name=t "
    "t. ! queue ! videoconvert ! videoscale ! video/x-raw,width={udp_width},height={udp_height} ! queue ! "
    "omxh264enc target-bitrate={udp_bitrate} control-rate=1 interval-intraframes=50 ! queue ! "
    "video/x-h264, profile=baseline ! rtph264pay ! udpsink host={udp_host} port={udp_port} sync=false async=false "
    "t. ! queue ! videoconvert ! videoscale ! video/x-raw,width={out_width},height={out_height} ! queue ! "
    "omxh264enc target-bitrate={out_bitrate} control-rate=1 interval-intraframes=50 ! queue ! "
    'video/x-h264,profile=baseline,stream-format="byte-stream" ! queue ! appsink',
}


def change_segment_config(config_dir):
    """Change the ips in all the config files the segment is using them.
    It will count on the ip of the pi"""
    # Get the local IP address's third octet
    ip_address = subprocess.check_output("hostname -I | awk '{for (i=1; i<=NF; i++) if ($i ~ /^192\\.168\\./) print $i}'", shell=True).decode().strip().split()[0]
    third_octet_new = ip_address.split(".")[2]
    print(config_dir)

    # Regular expression to match IP addresses
    ip_regex = re.compile(r"(\d+\.\d+\.)(\d+)(\.\d+)")

    with open(config_dir, "r") as f:
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
    with open(config_dir, "w") as f:
        f.writelines(updated_content)

    # Print changes made
    if changes_made_in_file:
        logger.info("Updated {} with a new ip address of {}".format(config_dir, third_octet_new))
    else:
        logger.info("No changes needed for {}.".format(config_dir))


def create_stream(config_file):
    change_segment_config(config_file)
    parser = SafeConfigParser()
    parser.read(config_file)
    kwargs = dict(parser.items("camera"))
    name = os.path.basename(os.path.splitext(config_file)[0])
    _type = parse_option("camera.type", str, **kwargs)
    assert _type in list(gst_commands.keys()), "Unrecognized camera type '{}'.".format(_type)
    if _type == "h264/rtsp":
        out_width, out_height = [int(x) for x in parse_option("camera.output.shape", str, "640x480", **kwargs).split("x")]
        config = {
            "ip": (parse_option("camera.ip", str, "192.168.1.64", **kwargs)),
            "port": (parse_option("camera.port", int, 554, **kwargs)),
            "user": (parse_option("camera.user", str, "user1", **kwargs)),
            "password": (parse_option("camera.password", str, "HaikuPlot876", **kwargs)),
            "path": (parse_option("camera.path", str, "/Streaming/Channels/103", **kwargs)),
        }
    else:
        _type = "raw/usb/h264/udp"
        src_width, src_height = [int(x) for x in parse_option("camera.source.shape", str, "640x480", **kwargs).split("x")]
        udp_width, udp_height = [int(x) for x in parse_option("camera.udp.shape", str, "320x240", **kwargs).split("x")]
        out_width, out_height = [int(x) for x in parse_option("camera.output.shape", str, "480x320", **kwargs).split("x")]
        config = {
            "uri": (parse_option("camera.uri", str, "/dev/video0", **kwargs)),
            "src_width": src_width,
            "src_height": src_height,
            "video_flip": (parse_option("camera.flip.method", str, "none", **kwargs)),
            "udp_width": udp_width,
            "udp_height": udp_height,
            "udp_bitrate": (parse_option("camera.udp.bitrate", int, 1024000, **kwargs)),
            "udp_host": (parse_option("camera.udp.host", str, "192.168.1.100", **kwargs)),
            "udp_port": (parse_option("camera.udp.port", int, 5000, **kwargs)),
            "out_width": out_width,
            "out_height": out_height,
            "out_bitrate": (parse_option("camera.output.bitrate", int, 1024000, **kwargs)),
        }
    _command = gst_commands.get(_type).format(**config)
    _socket_ref = parse_option("camera.output.class", str, "http-live", **kwargs)
    logger.info("Socket '{}' ref '{}' gst command={}".format(name, _socket_ref, _command))
    return (create_video_source(name, shape=(out_height, out_width, 3), command=_command), _socket_ref)


def main():
    parser = argparse.ArgumentParser(description="Camera web-socket server.")
    parser.add_argument("--config", type=str, default="/config/stream.ini", help="Configuration file.")
    parser.add_argument("--port", type=int, default=9101, help="Socket port.")
    args = parser.parse_args()

    config_file = args.config
    if os.path.exists(config_file) and os.path.isfile(config_file):
        video_stream, socket_type = create_stream(config_file)
        application = CameraApplication(stream=video_stream, event=quit_event)

        threads = [threading.Thread(target=application.run)]
        if quit_event.is_set():
            return 0

        [t.start() for t in threads]

        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        asyncio.set_event_loop(asyncio.new_event_loop())

        io_loop = ioloop.IOLoop.instance()
        class_ref = HttpLivePlayerVideoSocket if socket_type == "http-live" else JMuxerVideoStreamSocket
        web_app = web.Application([(r"/", class_ref, dict(video_source=video_stream, io_loop=io_loop))])
        rear_server = web.HTTPServer(web_app, xheaders=True)
        rear_server.bind(args.port)
        rear_server.start()
        logger.info("Web service started on port {}.".format(args.port))
        io_loop.start()

        logger.info("Waiting on threads to stop.")
        [t.join() for t in threads]
    else:
        shutil.copyfile("/app/stream/camera.template", config_file)
        logger.info("Created a new camera configuration file from template.")
        while not quit_event.is_set():
            time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(format=log_format, datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
