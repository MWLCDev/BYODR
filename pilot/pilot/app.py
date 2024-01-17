from __future__ import absolute_import

import argparse
import asyncio
import glob
import logging
import multiprocessing
import os
import signal
import threading

from six.moves.configparser import SafeConfigParser
from tornado import web, ioloop
from tornado.httpserver import HTTPServer
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from byodr.utils import Application, ApplicationExit
from byodr.utils.ipc import JSONPublisher, LocalIPCServer, json_collector, JSONServerThread
from byodr.utils.navigate import FileSystemRouteDataSource, ReloadableDataSource
from byodr.utils.option import parse_option
from byodr.utils.usbrelay import SearchUsbRelayFactory, StaticRelayHolder, TransientMemoryRelay
from .core import CommandProcessor
from .relay import RealMonitoringRelay, NoopMonitoringRelay
from .web import RelayControlRequestHandler, RelayConfigRequestHandler


logger = logging.getLogger(__name__)

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())

quit_event = multiprocessing.Event()


def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


class PilotApplication(Application):
    def __init__(self, event, processor, relay, config_dir=os.getcwd()):
        super(PilotApplication, self).__init__(quit_event=event)
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
        self.coms_receiver = None
        self.movement_commands = None
        self._init(relay)

    def _init(self, _relay):
        if _relay.is_attached():
            self._holder = StaticRelayHolder(relay=_relay, default_channels=(0, 1))
            self._monitor = RealMonitoringRelay(relay=self._holder, config_dir=self._config_dir)
        else:
            _relay = TransientMemoryRelay()
            self._holder = StaticRelayHolder(relay=_relay, default_channels=())
            self._monitor = NoopMonitoringRelay()

    def _config(self):
        parser = SafeConfigParser()
        [parser.read(_f) for _f in glob.glob(os.path.join(self._config_dir, '*.ini'))]
        cfg = dict(parser.items('pilot')) if parser.has_section('pilot') else {}
        cfg.update(dict(parser.items('relay')) if parser.has_section('relay') else {})
        self.logger.info(cfg)
        return cfg

    def _set_pulse_channels(self, **kwargs):
        _pulse_channels = []
        # The channel index is zero based in the code and 1-based in the configuration.
        if parse_option('primary.channel.3.operation', str, '', [], **kwargs) == 'pulse':
            _pulse_channels.append(2)
        if parse_option('primary.channel.4.operation', str, '', [], **kwargs) == 'pulse':
            _pulse_channels.append(3)
        self._holder.set_pulse_channels(_pulse_channels)

    def get_process_frequency(self):
        return self._processor.get_frequency()

    def get_relay_holder(self):
        return self._holder

    def setup(self):
        if self.active():
            _cfg = self._config()
            self._set_pulse_channels(**_cfg)
            _errors = self._monitor.setup()
            _restarted = self._processor.restart(**_cfg)
            if _restarted:
                self.ipc_server.register_start(_errors + self._processor.get_errors())
                _frequency = self._processor.get_frequency()
                self.set_hz(_frequency)
                self.logger.info("Processing at {} Hz - patience is {:2.2f} ms.".format(_frequency, self._processor.get_patience_ms()))

    def finish(self):
        self._monitor.quit()
        self._processor.quit()

    # def run(self):
    #     from byodr.utils import Profiler
    #     profiler = Profiler()
    #     with profiler():
    #         super(PilotApplication, self).run()
    #     profiler.dump_stats('/config/pilot.stats')

    def step(self):
        coms = self.coms_receiver()
        commands = (coms, self.ros(), self.vehicle(), self.inference())
        pilot = self._processor.next_action(*commands)
        # print(f"Sending command to relay.py: {pilot}, {coms}.")
        self._monitor.step(pilot, coms)

        if pilot is not None:
            self.publisher.publish(pilot)
        chat = self.ipc_chatter()
        if chat is not None:
            if chat.get('command') == 'restart':
                self.setup()


def main():
    parser = argparse.ArgumentParser(description='Pilot.')
    parser.add_argument('--name', type=str, default='none', help='Process name.')
    parser.add_argument('--config', type=str, default='/config', help='Config directory path.')
    parser.add_argument('--routes', type=str, default='/routes', help='Directory with the navigation routes.')
    args = parser.parse_args()

    _relay = SearchUsbRelayFactory().get_relay()
    logger.info("The USB Relay is {} attached.".format('well' if _relay.is_attached() else 'not'))

    route_store = ReloadableDataSource(FileSystemRouteDataSource(directory=args.routes, load_instructions=True))
    application = PilotApplication(quit_event, processor=CommandProcessor(route_store), relay=_relay, config_dir=args.config)

    coms_receiver = json_collector(url='ipc:///byodr/coms_to_pilot.sock', topic=b'aav/coms/input', event=quit_event)
    ros = json_collector(url='ipc:///byodr/ros.sock', topic=b'aav/ros/input', hwm=10, pop=True, event=quit_event)
    vehicle = json_collector(url='ipc:///byodr/vehicle.sock', topic=b'aav/vehicle/state', event=quit_event)
    inference = json_collector(url='ipc:///byodr/inference.sock', topic=b'aav/inference/state', event=quit_event)
    ipc_chatter = json_collector(url='ipc:///byodr/teleop_c.sock', topic=b'aav/teleop/chatter', pop=True, event=quit_event)

    application.coms_receiver = lambda: coms_receiver.get()
    application.ros = lambda: ros.get()
    application.vehicle = lambda: vehicle.get()
    application.inference = lambda: inference.get()
    application.ipc_chatter = lambda: ipc_chatter.get()
    application.publisher = JSONPublisher(url='ipc:///byodr/pilot.sock', topic='aav/pilot/output')
    application.ipc_server = LocalIPCServer(url='ipc:///byodr/pilot_c.sock', name='pilot', event=quit_event)


    threads = [coms_receiver, ros, vehicle, inference, ipc_chatter, application.ipc_server, threading.Thread(target=application.run)]
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
        main_app = web.Application([
            (r"/teleop/pilot/controls/relay/state", RelayControlRequestHandler, dict(relay_holder=_holder)),
            (r"/teleop/pilot/controls/relay/conf", RelayConfigRequestHandler, dict(relay_holder=_holder))
        ])
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
    logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
    logging.getLogger().setLevel(logging.INFO)
    main()
