from __future__ import absolute_import

import argparse
import asyncio
import glob
import logging
import multiprocessing
import os
import signal
import threading
import logging
import traceback
import os
import glob
import signal
import multiprocessing
import collections
from byodr.utils import Application, ApplicationExit
from byodr.utils.gpio_relay import ThreadSafeGpioRelay
from byodr.utils.ipc import JSONPublisher, LocalIPCServer, json_collector
from byodr.utils.navigate import FileSystemRouteDataSource, ReloadableDataSource
from byodr.utils.option import parse_option
from byodr.utils.usbrelay import SearchUsbRelayFactory, StaticRelayHolder, TransientMemoryRelay
from six.moves.configparser import SafeConfigParser
from tornado import ioloop, web
from tornado.httpserver import HTTPServer
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from .core import CommandProcessor
from .relay import NoopMonitoringRelay, RealMonitoringRelay
from .web import RelayConfigRequestHandler, RelayControlRequestHandler

logger = logging.getLogger(__name__)

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


class PilotApplication(Application):
    def __init__(self, event, processor, config_dir=os.getcwd(), hz=100):
        super(PilotApplication, self).__init__(quit_event=event, run_hz=hz)
        self._config_dir = config_dir
        self._processor = processor
        self._monitor = None
        self._holder = None
        self.publisher = None
        self.ipc_server = None
        self.ipc_chatter = None
        self.teleop = None
        self.ros = None
        self.vehicle = None
        self.inference = None
        self._check_relay_type()

    def _init_relay(self, _relay):
        self._holder = StaticRelayHolder(relay=_relay, default_channels=(0, 1))
        self._monitor = RealMonitoringRelay(relay=self._holder, config_dir=self._config_dir)

    def _check_relay_type(self):
        try:
            _cfg = self._config()
            gpio_relay = _cfg.get("driver.gpio_relay", "false").strip().lower() == "true"  # in case it is saved in lower case from JS in TEL side
            if gpio_relay:
                relay = ThreadSafeGpioRelay()
                logger.info("Initialized GPIO Relay")
            else:
                relay = SearchUsbRelayFactory().get_relay()
                logger.info("Initialized USB Relay")
                assert relay.is_attached(), "The relay device is not attached."

            self._init_relay(relay)
        except AssertionError as e:
            logger.error("Relay initialization error: %s", e)
            self.quit()
        except Exception as e:
            logger.error("Unexpected error during relay type checking: %s", e)
            self.quit()

    def _config(self):
        try:
            parser = SafeConfigParser()
            [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, "*.ini"))]
            cfg = dict(parser.items("pilot")) if parser.has_section("pilot") else {}
            cfg.update(dict(parser.items("relay")) if parser.has_section("relay") else {})
            return cfg
        except Exception as e:
            logger.error("Error reading configuration: %s", e)
            self.quit()

    def _set_pulse_channels(self, **kwargs):
        try:
            _pulse_channels = []
            # The channel index is zero based in the code and 1-based in the configuration.
            if parse_option("primary.channel.3.operation", str, "", [], **kwargs) == "pulse":
                _pulse_channels.append(2)
            if parse_option("primary.channel.4.operation", str, "", [], **kwargs) == "pulse":
                _pulse_channels.append(3)
            self._holder.set_pulse_channels(_pulse_channels)
        except Exception as e:
            logger.error("Error setting pulse channels: %s", e)
            self.quit()

    def get_process_frequency(self):
        return self._processor.get_frequency()

    def get_relay_holder(self):
        return self._holder

    def setup(self):
        try:
            if self.active():
                _cfg = self._config()
                self._set_pulse_channels(**_cfg)
                _errors = self._monitor.setup()
                _restarted = self._processor.restart(**_cfg)
                if _restarted:
                    self.ipc_server.register_start(_errors + self._processor.get_errors())
                    _frequency = self._processor.get_frequency()
                    self.set_hz(_frequency)
                    logger.info(f"Processing at {_frequency} Hz - patience is {self._processor.get_patience_ms():2.2f} ms.")
        except Exception as e:
            logger.error("Error during setup: %s", e)
            self.quit()

    def finish(self):
        self._monitor.quit()
        self._processor.quit()

    def step(self):
        try:
            teleop = self.teleop()
            commands = (teleop, self.ros(), self.vehicle(), self.inference())
            pilot = self._processor.next_action(*commands)
            self._monitor.step(pilot, teleop)
            if pilot is not None:
                self.publisher.publish(pilot)
            chat = self.ipc_chatter()
            if chat is not None:
                if chat.get("command") == "restart":
                    self.setup()
        except Exception as e:
            logger.error("Error during step: %s", e)
            self.quit()


def main():
    parser = argparse.ArgumentParser(description="Pilot.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")
    parser.add_argument("--routes", type=str, default="/routes", help="Directory with the navigation routes.")
    args = parser.parse_args()

    route_store = ReloadableDataSource(FileSystemRouteDataSource(directory=args.routes, load_instructions=True))
    application = PilotApplication(quit_event, processor=CommandProcessor(route_store), config_dir=args.config)

    teleop = json_collector(url="ipc:///byodr/teleop.sock", topic=b"aav/teleop/input", event=quit_event)
    ros = json_collector(url="ipc:///byodr/ros.sock", topic=b"aav/ros/input", hwm=10, pop=True, event=quit_event)
    vehicle = json_collector(url="ipc:///byodr/vehicle.sock", topic=b"aav/vehicle/state", event=quit_event)
    inference = json_collector(url="ipc:///byodr/inference.sock", topic=b"aav/inference/state", event=quit_event)
    ipc_chatter = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=quit_event)

    application.teleop = lambda: teleop.get()
    application.ros = lambda: ros.get()
    application.vehicle = lambda: vehicle.get()
    application.inference = lambda: inference.get()
    application.ipc_chatter = lambda: ipc_chatter.get()
    application.publisher = JSONPublisher(url="ipc:///byodr/pilot.sock", topic="aav/pilot/output")
    application.ipc_server = LocalIPCServer(url="ipc:///byodr/pilot_c.sock", name="pilot", event=quit_event)
    threads = [teleop, ros, vehicle, inference, ipc_chatter, application.ipc_server, threading.Thread(target=application.run)]
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
        # The api has partial control of the relay.
        _holder = application.get_relay_holder()
        main_app = web.Application(
            [(r"/teleop/pilot/controls/relay/state", RelayControlRequestHandler, dict(relay_holder=_holder)), (r"/teleop/pilot/controls/relay/conf", RelayConfigRequestHandler, dict(relay_holder=_holder))]
        )
        http_server = HTTPServer(main_app, xheaders=True)
        http_server.bind(8082)
        http_server.start()
        logger.info("Pilot web services starting on port 8082.")
        io_loop.start()
    except KeyboardInterrupt:
        quit_event.set()
    finally:
        _periodic.stop()

    route_store.quit()
    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s:%(lineno)d %(funcName)s %(threadName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    main()
