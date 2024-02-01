from __future__ import absolute_import

import argparse
import glob
import logging
import os
import sys
import threading

import cv2
import numpy as np
# For operators see: https://github.com/glenfletcher/Equation/blob/master/Equation/equation_base.py
from Equation import Expression
from scipy.special import softmax
from six.moves import range
from sklearn.metrics.pairwise import cosine_distances

from byodr.utils import timestamp, Configurable, Application
from byodr.utils.ipc import CameraThread, JSONPublisher, LocalIPCServer, json_collector
from byodr.utils.navigate import FileSystemRouteDataSource, ReloadableDataSource
from byodr.utils.option import parse_option, PropertyError
from .image import get_registered_function
from .torched import DynamicMomentum, TRTDriver

if sys.version_info > (3,):
    from configparser import ConfigParser as SafeConfigParser
else:
    from six.moves.configparser import SafeConfigParser

logger = logging.getLogger(__name__)


class RouteMemory(object):
    def __init__(self):
        self._recognition_threshold = 0
        self._num_points = 0
        self._num_codes = 0
        self._navigation_point = None
        # Image is locked in when threshold reached.
        self._tracking = None
        self._evidence = None
        # Image id index to navigation point id.
        self._code_points = None
        # Image id index to features.
        self._code_book = None
        self._destination_keys = None
        self._destination_values = None

    def _evidence_reset(self):
        self._evidence = np.ones(self._num_codes, dtype=np.float32)

    def set_threshold(self, value):
        self._recognition_threshold = value

    def reset(self, n_points=0, code_points=None, coordinates=None, keys=None, values=None):
        self._navigation_point = None
        self._tracking = None
        self._num_points = n_points
        self._num_codes = 0 if code_points is None else len(code_points)
        self._code_points = None if code_points is None else np.array(code_points)
        self._code_book = None if coordinates is None else np.array(coordinates)
        self._destination_keys = None if keys is None else np.array(keys)
        self._destination_values = None if values is None else np.array(values)
        self._evidence_reset()

    def is_open(self):
        return self._code_book is not None

    def _distances(self, features):
        # return np.clip(abs(cosine_distances(self._code_book, np.reshape(features, [1, -1])).flatten() - self._cosine_diagonal), 0, 1)
        return cosine_distances(self._code_book, np.reshape(features, [1, -1])).flatten()

    def match(self, features, query):
        code_points = self._code_points
        _before_match = self._navigation_point is None
        _point, _previous, _next = (-1, -1, -1) if _before_match else self._navigation_point
        _threshold = self._recognition_threshold

        # The beliefs incorporate local information through the network probabilities.
        _p_out = softmax(np.matmul(query.reshape([1, -1]), self._destination_keys.T)).flatten()
        # The features are those of the source coordinates.
        _errors = self._distances(features)
        _beliefs = _p_out * np.exp(-np.e * _errors)
        self._evidence = np.minimum(self._evidence, _errors)

        # Select the destination from the next expected navigation point.
        _image = self._tracking
        if _image is None:
            _image = _errors.argmin() if _before_match else np.where(code_points == _next, _errors, 2).argmin()

        # Allow for a better match in case it is tracking the wrong image.
        _competitor = np.where(np.logical_or.reduce([code_points == _point, code_points == _previous]), -1, _beliefs).argmax()

        _match = None
        image_evidence = self._evidence[_image]
        other_evidence = self._evidence[_competitor]
        _tracking = self._tracking is not None

        _nlf = .90
        if _tracking and _errors[_image] > np.power(image_evidence, _nlf):
            _match = code_points[_image]
            self._tracking = None
        elif not _tracking and image_evidence < _threshold:
            self._tracking = _image
        elif not _tracking and other_evidence < _threshold and _errors[_competitor] > np.power(other_evidence, _nlf):
            _image = _competitor
            _match = code_points[_competitor]
            self._tracking = None

        if _match is not None and _point != _match:
            logger.info("Match {} error {:.2f} evidence {:.2f}".format(_match, _errors[_image], self._evidence[_image]))
            n_points = self._num_points
            self._navigation_point = _match, ((_match - 1) % n_points), ((_match + 1) % n_points)
            self._evidence_reset()

        _distance = _errors[_image]
        _destination = self._destination_values[_image]
        return _match, _image, _distance, _destination


class Navigator(object):
    def __init__(self, user_directory, internal_directory, routes_directory):
        self._model_directories = [user_directory, internal_directory]
        self._routes_directory = routes_directory
        self._lock = threading.Lock()
        self._quit_event = threading.Event()
        self._memory = RouteMemory()
        self._network = None
        self._store = None
        self._fn_dave_image = None
        self._fn_alex_image = None
        self._gumbel = None
        self._destination = None

    def _create_network(self, gpu_id=0, runtime_compilation=1):
        user_directory, internal_directory = self._model_directories
        network = TRTDriver(user_directory, internal_directory, gpu_id=gpu_id, runtime_compilation=runtime_compilation)
        return network

    def _pull_image_features(self, image):
        return self._network.features(dave_image=self._fn_dave_image(image),
                                      alex_image=self._fn_alex_image(image))

    def _route_open(self, route):
        # This may take a while.
        if not self._quit_event.is_set():
            with self._lock:
                if route != self._store.get_selected_route():
                    self._memory.reset()
                    self._gumbel = None
                    self._destination = None
                    self._store.open(route)
                    num_points = len(self._store)
                    if num_points > 0:
                        _images = self._store.list_all_images()
                        _codes, _coordinates, _keys, _values = [], [], [], []
                        for im_id in range(len(_images)):
                            _codes.append(self._store.get_image_navigation_point_id(im_id))
                            _c, _k, _v = self._pull_image_features(_images[im_id])
                            _coordinates.append(_c)
                            _keys.append(_k)
                            _values.append(_v)
                        self._memory.reset(num_points, _codes, _coordinates, _keys, _values)

    def _check_state(self, route=None):
        if route is None:
            self._store.close()
        elif route not in self._store.list_routes():
            threading.Thread(target=self._store.load_routes).start()
        elif route != self._store.get_selected_route():
            threading.Thread(target=self._route_open, args=(route,)).start()

    def recompile(self):
        with self._lock:
            if self._network is not None and self._network.will_compile():
                self._network.reactivate()

    def restart(self, fn_dave_image, fn_alex_image, recognition_threshold=0, gpu_id=0, runtime_compilation=1):
        self._quit_event.clear()
        with self._lock:
            _load_image = (lambda fname: self._fn_alex_image(cv2.imread(fname)))
            _store = FileSystemRouteDataSource(self._routes_directory, fn_load_image=_load_image, load_instructions=False)
            self._store = ReloadableDataSource(_store)
            self._fn_dave_image = fn_dave_image
            self._fn_alex_image = fn_alex_image
            if self._network is not None:
                self._network.deactivate()
            self._network = self._create_network(gpu_id, runtime_compilation)
            self._network.activate()
            self._store.load_routes()
            self._memory.reset()
            self._memory.set_threshold(recognition_threshold)
            self._destination = None

    def forward(self, image, route=None):
        # This runs at the service process frequency.
        self._check_state(route)
        _dave_img = self._fn_dave_image(image)
        _alex_img = self._fn_alex_image(image)
        _destination = self._destination
        _command = 0 if _destination is None else 1
        _out = self._network.forward(dave_image=_dave_img,
                                     alex_image=_alex_img,
                                     maneuver_command=_command,
                                     destination=_destination)
        action, critic, surprise, command, path, brake, brake_critic, coordinates, query = _out

        # noinspection PyUnusedLocal
        nav_point_id, nav_image_id, nav_distance, _destination = None, None, None, None
        _acquired = self._lock.acquire(False)
        try:
            if _acquired and self._store.is_open() and self._memory.is_open():
                nav_point_id, nav_image_id, nav_distance, _destination = self._memory.match(coordinates, query)
        finally:
            if _acquired:
                self._lock.release()

        self._destination = _destination
        return action, critic, surprise, brake, brake_critic, nav_point_id, nav_image_id, nav_distance, command, path

    def quit(self):
        # Store and network are thread-safe.
        self._quit_event.set()
        if self._store is not None:
            self._store.quit()
        if self._network is not None:
            self._network.deactivate()


def _norm_scale(v, min_=0., max_=1.):
    """Zero values below the minimum but let values larger than the maximum be scaled up. """
    return abs(max(0., v - min_) / (max_ - min_))


def _null_expression(*args):
    logger.warning("Null expression used on args '{}'".format(args))
    return 100


def _build_expression(key, default_value, errors, **kwargs):
    _expression = _null_expression
    _equation = parse_option(key, str, default_value, errors, **kwargs)
    try:
        _expression = Expression(_equation)
        _expression(surprise=0, loss=0)
    except (TypeError, IndexError, ZeroDivisionError) as te:
        errors.append(PropertyError(key, str(te)))
    return _expression


class TFRunner(Configurable):
    def __init__(self, navigator):
        super(TFRunner, self).__init__()
        self._gpu_id = 0
        self._navigator = navigator
        self._process_frequency = 10
        self._steering_scale_left = 1
        self._steering_scale_right = 1
        self._steer_confidence_filter = None
        self._brake_confidence_filter = None
        self._total_penalty_filter = None
        self._fn_steer_mu = None
        self._fn_brake_mu = None

    def get_gpu(self):
        return self._gpu_id

    def get_frequency(self):
        return self._process_frequency

    def internal_quit(self, restarting=False):
        self._navigator.quit()

    def internal_start(self, **kwargs):
        _errors = []
        self._gpu_id = parse_option('gpu.id', int, 0, _errors, **kwargs)
        self._process_frequency = parse_option('clock.hz', int, 20, _errors, **kwargs)
        self._steering_scale_left = parse_option('driver.dnn.steering.scale.left', lambda x: abs(float(x)), -1, _errors, **kwargs)
        self._steering_scale_right = parse_option('driver.dnn.steering.scale.right', float, 1, _errors, **kwargs)
        _penalty_up_momentum = parse_option('driver.autopilot.filter.momentum.up', float, 0.35, _errors, **kwargs)
        _penalty_down_momentum = parse_option('driver.autopilot.filter.momentum.down', float, 0.25, _errors, **kwargs)
        _penalty_ceiling = parse_option('driver.autopilot.filter.ceiling', float, 2.0, _errors, **kwargs)
        self._total_penalty_filter = DynamicMomentum(up=_penalty_up_momentum, down=_penalty_down_momentum, ceiling=_penalty_ceiling)
        self._steer_confidence_filter = DynamicMomentum(up=_penalty_up_momentum, down=_penalty_down_momentum, ceiling=1.0)
        self._brake_confidence_filter = DynamicMomentum(up=_penalty_up_momentum, down=_penalty_down_momentum, ceiling=1.0)
        self._fn_steer_mu = _build_expression(
            'driver.dnn.steer.mu.equation', '(7.0 * (-0.50 + surprise + loss)) **7', _errors, **kwargs
        )
        self._fn_brake_mu = _build_expression(
            'driver.dnn.brake.mu.equation', '2.0 * surprise + 2.5 * (loss > 0.75) * (loss - 0.75)', _errors, **kwargs
        )
        _fn_dave_image = get_registered_function('dnn.image.transform.dave', 'dave__320_240__200_66__0', _errors, **kwargs)
        _fn_alex_image = get_registered_function('dnn.image.transform.alex', 'alex__200_100', _errors, **kwargs)
        _nav_threshold = parse_option('navigator.point.recognition.threshold', float, 0.100, _errors, **kwargs)
        _rt_compile = parse_option('runtime.graph.compilation', int, 1, _errors, **kwargs)
        self._navigator.restart(fn_dave_image=_fn_dave_image,
                                fn_alex_image=_fn_alex_image,
                                recognition_threshold=_nav_threshold,
                                gpu_id=self._gpu_id,
                                runtime_compilation=_rt_compile)
        return _errors

    def _dnn_steering(self, raw):
        return raw * (self._steering_scale_left if raw < 0 else self._steering_scale_right)

    def forward(self, image, route=None):
        _out = self._navigator.forward(image, route)
        action, critic, surprise, brake, brake_critic, nav_point_id, nav_image_id, nav_distance, command, path = _out
        _command_index = int(np.argmax(command))
        _steer_penalty = min(1, max(0, self._fn_steer_mu(surprise=max(0, surprise), loss=abs(surprise - critic))))
        _obstacle_penalty = min(1, max(0, self._fn_brake_mu(surprise=max(0, brake), loss=max(0, brake_critic))))
        # The total penalty is smoothed over the instant values.
        _total_running_penalty = min(1, max(0, self._total_penalty_filter.calculate(_steer_penalty + _obstacle_penalty)))
        # Smooth the instant individual values for reporting purposes.
        _normalized_brake_critic = self._fn_brake_mu(surprise=0, loss=max(0, brake_critic))
        _steer_running_confidence = 1. - min(1, max(0, self._steer_confidence_filter.calculate(_steer_penalty)))
        _brake_running_confidence = 1. - min(1, max(0, self._brake_confidence_filter.calculate(_normalized_brake_critic)))
        return dict(time=timestamp(),
                    action=float(self._dnn_steering(action)),
                    obstacle=float(brake),
                    surprise_out=float(surprise),
                    critic_out=float(critic),
                    brake_critic_out=float(brake_critic),
                    steer_penalty=float(_steer_penalty),
                    brake_penalty=float(_obstacle_penalty),
                    total_penalty=float(_total_running_penalty),
                    steer_confidence=float(_steer_running_confidence),
                    brake_confidence=float(_brake_running_confidence),
                    internal=[float(0)],
                    navigation_point=int(-1 if nav_point_id is None else nav_point_id),
                    navigation_image=int(-1 if nav_image_id is None else nav_image_id),
                    navigation_distance=float(1 if nav_distance is None else nav_distance),
                    navigation_command=int(_command_index),
                    navigation_path=[float(v) for v in path]
                    )


class InferenceApplication(Application):
    def __init__(self, runner=None, config_dir=os.getcwd(), internal_models=os.getcwd(), user_models=None, navigation_routes=None):
        super(InferenceApplication, self).__init__()
        self._config_dir = config_dir
        self._internal_models = internal_models
        self._user_models = user_models
        if user_models is not None and not os.path.exists(user_models):
            _mask = os.umask(000)
            os.makedirs(user_models, mode=0o775)
            os.umask(_mask)
        if runner is None:
            runner = TFRunner(navigator=Navigator(user_models, internal_models, navigation_routes))
        self._runner = runner
        self.publisher = None
        self.camera = None
        self.ipc_server = None
        self.teleop = None
        self.ipc_chatter = None

    @staticmethod
    def _glob(directory, pattern):
        return glob.glob(os.path.join(directory, pattern))

    def _config(self):
        parser = SafeConfigParser()
        # Ignore the teleop managed configuration use a location not accessible via the ui. Overrides come last.
        _override = os.path.join(self._config_dir, 'inference')
        [parser.read(_f) for _f in self._glob(self._internal_models, '*.ini') + self._glob(_override, '*.ini')]
        cfg = dict(parser.items('inference')) if parser.has_section('inference') else {}
        logger.info(cfg)
        return cfg

    def get_process_frequency(self):
        return self._runner.get_frequency()

    def setup(self):
        if self.active():
            _restarted = self._runner.restart(**self._config())
            if _restarted:
                self.ipc_server.register_start(self._runner.get_errors())
                _frequency = self._runner.get_frequency()
                self.set_hz(_frequency)
                self.logger.info("Processing at {} Hz on gpu {}.".format(_frequency, self._runner.get_gpu()))

    def finish(self):
        self._runner.quit()

    # def run(self):
    #     from byodr.utils import Profiler
    #     profiler = Profiler()
    #     with profiler():
    #         super(InferenceApplication, self).run()
    #     profiler.dump_stats('/config/inference.stats')

    def step(self):
        # Leave the state as is on empty teleop state.
        c_teleop = self.teleop()
        image = self.camera.capture()[-1]
        if image is not None:
            # The teleop service is the authority on route state.
            c_route = None if c_teleop is None else c_teleop.get('navigator').get('route')
            state = self._runner.forward(image=image, route=c_route)
            state['_fps'] = self.get_actual_hz()
            self.publisher.publish(state)
        chat = self.ipc_chatter()
        if chat is not None:
            if chat.get('command') == 'restart':
                self.setup()


def main():
    parser = argparse.ArgumentParser(description='Inference server.')
    parser.add_argument('--config', type=str, default='/config', help='Config directory path.')
    parser.add_argument('--internal', type=str, default='/models', help='Directory with the default inference models.')
    parser.add_argument('--user', type=str, default='/user_models', help='Directory with the user inference models.')
    parser.add_argument('--routes', type=str, default='/routes', help='Directory with the navigation routes.')
    args = parser.parse_args()

    application = InferenceApplication(config_dir=args.config,
                                       internal_models=args.internal,
                                       user_models=args.user,
                                       navigation_routes=args.routes)
    quit_event = application.quit_event

    teleop = json_collector(url='ipc:///byodr/teleop.sock', topic=b'aav/teleop/input', event=quit_event)
    ipc_chatter = json_collector(url='ipc:///byodr/teleop_c.sock', topic=b'aav/teleop/chatter', pop=True, event=quit_event)

    application.publisher = JSONPublisher(url='ipc:///byodr/inference.sock', topic='aav/inference/state')
    application.camera = CameraThread(url='ipc:///byodr/camera_0.sock', topic=b'aav/camera/0', event=quit_event)
    application.ipc_server = LocalIPCServer(url='ipc:///byodr/inference_c.sock', name='inference', event=quit_event)
    application.teleop = lambda: teleop.get()
    application.ipc_chatter = lambda: ipc_chatter.get()

    threads = [teleop, ipc_chatter, application.camera, application.ipc_server]
    if quit_event.is_set():
        return 0

    [t.start() for t in threads]
    application.run()

    logger.info("Waiting on threads to stop.")
    [t.join() for t in threads]


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
    logging.getLogger().setLevel(logging.INFO)
    main()
