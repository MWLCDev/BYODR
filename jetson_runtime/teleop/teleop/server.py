#!/usr/bin/env python

from __future__ import absolute_import

import collections
import fcntl
import json
import logging
import os
import threading
import time
import traceback
from io import open

import cv2
import numpy as np
import tornado
import tornado.ioloop
import tornado.web
from BYODR_utils.common import timestamp
from BYODR_utils.common.ssh import Router
from six.moves import range
from six.moves.configparser import SafeConfigParser
from tornado import web, websocket

from .tel_utils import OverviewConfidence

logger = logging.getLogger(__name__)


import tornado.websocket

latest_message = {}


class LatestImageHandler(tornado.web.RequestHandler):
    def initialize(self, path, following_utils):
        self.image_save_path = path
        self.following_utils = following_utils  # Store the passed following_utils

    def get(self):
        # Use the following_utils to get the current following state
        following_state = self.following_utils.get_following_state()

        # Only send the image if the following state is not "inactive"
        if following_state == "inactive":
            self.write("Following is inactive. No image to display.")
            self.set_status(204)  # No content
            self.finish()
            return

        # Set headers for the image response
        self.set_header("Content-Type", "image/jpeg")
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

        try:
            # Fetch all jpg files in the directory
            image_files = [f for f in os.listdir(self.image_save_path) if f.endswith(".jpg")]

            # Get full paths for the images
            full_paths = [os.path.join(self.image_save_path, f) for f in image_files]

            # Sort by creation time (latest first)
            full_paths.sort(key=os.path.getctime, reverse=True)

            if full_paths:
                latest_image = full_paths[0]

                # Try to read and serve the image
                try:
                    with open(latest_image, "rb") as img:
                        # Lock the file while reading to prevent conflicts
                        fcntl.flock(img, fcntl.LOCK_SH)
                        self.write(img.read())
                        fcntl.flock(img, fcntl.LOCK_UN)
                except IOError:
                    # Handle IO errors
                    self.write("Error accessing the image file.")
                    self.set_status(500)  # Internal Server Error
            else:
                self.write("No images available.")
        except Exception as e:
            self.write(f"Error fetching the latest image: {str(e)}")
            self.set_status(500)  # Internal Server Error
        finally:
            self.finish()


class FollowingHandler(web.RequestHandler):
    def initialize(self, **kwargs):
        self._fn_control = kwargs.get("fn_control")

    def post(self):
        command_text = self.get_body_argument("command", default=None)
        command_dict = {"following": command_text}
        self._fn_control.teleop_publish_to_following(command_dict)
        self.write({"status": "success", "time": timestamp()})

    def get(self):
        following_status = self._fn_control.get_following_state()
        self.write({"status": "success", "following_status": following_status})


class ControlServerSocket(websocket.WebSocketHandler):
    # There can be only one operator in control at any time.
    # Do not use a single variable since class attributes mutate to be instance attributes.
    operators = set()  # Keep track of the current operator

    def _has_operators(self):  # check if there are any operators
        return len(self.operators) > 0

    def _is_operator(self):
        return self in self.operators

    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):  # Initializes the WebSocket handler
        self._fn_control = kwargs.get("fn_control")

    def check_origin(self, origin):
        return True

    def data_received(self, chunk):
        pass

    def open(self, *args, **kwargs):
        self.operators.clear()  # Clear any previous operators
        self.operators.add(self)  # Make the current one operator
        logger.info("Operator {} connected.".format(self.request.remote_ip))

    def on_close(self):
        if self._is_operator():
            self.operators.clear()
        #     logger.info("Operator {} disconnected.".format(self.request.remote_ip))
        # else:
        #     logger.info("Viewer {} disconnected.".format(self.request.remote_ip))

    def on_message(self, json_message):
        msg = json.loads(json_message)
        _response = json.dumps(dict(control="viewer"))
        if self._is_operator():
            _response = json.dumps(dict(control="operator"))
            msg["time"] = timestamp()
            self._fn_control(msg)
        elif msg.get("_operator") == "force":
            self.operators.clear()
            self.operators.add(self)
            logger.info("Viewer {} took over control and is now operator.".format(self.request.remote_ip))
        try:
            self.write_message(_response)
        except websocket.WebSocketClosedError:
            pass


class ConfidenceHandler(websocket.WebSocketHandler):
    def initialize(self, inference_s, vehicle_s):
        self.inference = inference_s
        self.vehicle = vehicle_s

    def open(self):
        logger.info("Confidence websocket connection opened.")
        self.runner = OverviewConfidence(self.inference, self.vehicle)
        self.write_message("Connection established.")

    def on_message(self, message):
        if message == "start_confidence":
            self.runner.start()
            self.write_message("Received start")
        elif message == "stop_confidence":
            self.write_message("Received stopping command")
            self.write_message("loading")
            self.runner.stop()
            self.runner.process_data()
            self.write_message(self.runner.map_name)


class MessageServerSocket(websocket.WebSocketHandler):
    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):
        self._fn_state = kwargs.get("fn_state")

    def check_origin(self, origin):
        return True

    def data_received(self, chunk):
        pass

    def open(self, *args, **kwargs):
        pass

    def on_close(self):
        pass

    @staticmethod
    def _translate_driver(pilot, inference):
        if None in (pilot, inference):
            return 0
        ctl = pilot.get("driver")
        if ctl is None:
            return 0
        elif ctl == "driver_mode.teleop.direct":
            return 2
        elif ctl == "driver_mode.teleop.cruise":
            return 3
        elif ctl == "driver_mode.inference.dnn":
            return 5

    @staticmethod
    def _translate_recorder(recorder):
        if recorder is not None:
            if recorder.get("mode") == "record.mode.driving":
                return 551
            elif recorder.get("mode") == "record.mode.interventions":
                return 594
        return -999

    @staticmethod
    def _translate_instruction(index):
        if index == 3:
            return "intersection.ahead"
        elif index in (1, 2):
            return "intersection.left"
        elif index in (4, 5):
            return "intersection.right"
        else:
            return "general.fallback"

    @staticmethod
    def _translate_navigation_path(path, scope=5):
        # Scope: The frontend can handle a maximum of path elements only.
        if path is None:
            return 0, [0] * scope
        assert len(path) > scope
        _x = len(path) // scope
        return np.mean(path), [np.mean(path[i * _x : (i + 1) * _x]) for i in range(scope)]

    def on_message(self, *args):
        try:
            state = self._fn_state()
            pilot = None if state is None else state[0]
            vehicle = None if state is None else state[1]
            inference = None if state is None else state[2]
            recorder = None
            meters_per_second_to_km_per_hour = 3.6
            pilot_navigation_active = 0 if pilot is None else int(pilot.get("navigation_active", False))
            pilot_match_image = -1 if pilot is None else pilot.get("navigation_match_image", -1)
            pilot_match_distance = 1 if pilot is None else pilot.get("navigation_match_distance", 1)
            pilot_match_point = "" if pilot is None else pilot.get("navigation_match_point", "")
            inference_current_image = -1 if inference is None else inference.get("navigation_image", -1)
            inference_current_distance = -1 if inference is None else inference.get("navigation_distance", -1)
            inference_command = -1 if inference is None else inference.get("navigation_command", -1)
            inference_path = None if inference is None else inference.get("navigation_path")
            nav_direction, nav_path = self._translate_navigation_path(inference_path)
            response = {
                "ctl": self._translate_driver(pilot, inference),
                "ctl_activation": (0 if pilot is None else pilot.get("driver_activation_time", 0)),
                "inf_brake_critic": (0 if inference is None else inference.get("brake_critic_out")),
                "inf_brake": 0 if inference is None else inference.get("obstacle"),
                "inf_total_penalty": (0 if inference is None else inference.get("total_penalty")),
                "inf_steer_penalty": (0 if inference is None else inference.get("steer_penalty")),
                "inf_brake_penalty": (0 if inference is None else inference.get("brake_penalty")),
                "inf_surprise": (0 if inference is None else inference.get("surprise_out")),
                "inf_critic": 0 if inference is None else inference.get("critic_out"),
                "inf_hz": 0 if inference is None else inference.get("_fps"),
                "rec_act": False if recorder is None else recorder.get("active"),
                "rec_mod": self._translate_recorder(recorder),
                "ste": 0 if pilot is None else pilot.get("steering"),
                "thr": 0 if pilot is None else pilot.get("throttle"),
                "vel_y": (0 if vehicle is None else vehicle.get("velocity") * meters_per_second_to_km_per_hour),
                "geo_lat": 0 if vehicle is None else vehicle.get("latitude_geo"),
                "geo_long": 0 if vehicle is None else vehicle.get("longitude_geo"),
                "geo_head": 0 if vehicle is None else vehicle.get("heading"),
                "des_speed": (0 if pilot is None else pilot.get("desired_speed") * meters_per_second_to_km_per_hour),
                "max_speed": (0 if pilot is None else pilot.get("cruise_speed") * meters_per_second_to_km_per_hour),
                "head": 0 if vehicle is None else vehicle.get("heading"),
                "nav_active": pilot_navigation_active,
                "nav_point": pilot_match_point,
                "nav_image": [pilot_match_image, inference_current_image],
                "nav_distance": [pilot_match_distance, inference_current_distance],
                "nav_command": inference_command,
                "nav_direction": nav_direction,
                "nav_path": nav_path,
                "turn": self._translate_instruction(inference_command),
            }
            self.write_message(json.dumps(response))
        except Exception:
            logger.error("MessageServerSocket:on_message:{}".format(traceback.format_exc()))
            raise


def jpeg_encode(image, quality=95):
    """Higher quality leads to slightly more cpu load. Default cv jpeg quality is 95."""
    return cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])[1]


class CameraMJPegSocket(websocket.WebSocketHandler):
    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):
        self._fn_capture = kwargs.get("image_capture")
        self._black_img = np.zeros(shape=(320, 240, 3), dtype=np.uint8)
        self._calltrace = collections.deque(maxlen=1)
        self._calltrace.append(timestamp())

    def check_origin(self, origin):
        return True

    def data_received(self, chunk):
        pass

    def open(self, *args, **kwargs):
        _width, _height = 640, 480
        md = self._fn_capture()[0]
        if md is not None:
            _height, _width, _channels = md["shape"]
        self.write_message(json.dumps(dict(action="init", width=_width, height=_height)))

    def on_close(self):
        pass

    def on_message(self, message):
        try:
            request = json.loads(message)
            quality = int(request.get("quality", 90))
            md, img = self._fn_capture()
            _timestamp = self._calltrace[-1] if md is None else md.get("time")
            if _timestamp == self._calltrace[-1]:
                # Refrain from encoding and resending an old image.
                self.write_message(json.dumps(dict(action="wait")))
            else:
                # Always send something so the client is able to resume polling.
                self._calltrace.append(_timestamp)
                self.write_message(
                    jpeg_encode((self._black_img if img is None else img), quality).tobytes(),
                    binary=True,
                )
        except Exception as e:
            logger.error("Camera socket@on_message: {} {}".format(e, traceback.format_exc()))
            logger.error("JSON message:---\n{}\n---".format(message))


class NavImageHandler(web.RequestHandler):
    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):
        self._fn_get_image = kwargs.get("fn_get_image")
        self._black_img = np.zeros(shape=(1, 1, 3), dtype=np.uint8)
        self._jpeg_quality = 95

    def data_received(self, chunk):
        pass

    @tornado.gen.coroutine
    def get(self):
        try:
            image_id = int(self.get_query_argument("im"))
        except ValueError:
            image_id = -1
        image = self._fn_get_image(image_id)
        image = self._black_img if image is None else image
        chunk = jpeg_encode(image, quality=self._jpeg_quality)
        self.set_header("Content-Type", "image/jpeg")
        self.set_header("Content-Length", len(chunk))
        self.write(chunk.tobytes())


class UserOptions(object):
    def __init__(self, fname):
        self._fname = fname
        self._parser = SafeConfigParser()
        self.reload()

    def list_sections(self):
        return [s for s in self._parser.sections() if s != "inference"]

    def get_options(self, section):
        return dict(self._parser.items(section))

    def get_option(self, section, name):
        return self._parser.get(section, name)

    def set_option(self, section, name, value):
        self._parser.set(section, name, value)

    def reload(self):
        if os.path.exists(self._fname):
            self._parser.read(self._fname)

    def save(self):
        # The options could have been updated on disk.
        parser = SafeConfigParser()
        parser.read(self._fname)
        for section in parser.sections():
            for option in parser.options(section):
                if not self._parser.has_option(section, option):
                    self.set_option(section, option, parser.get(section, option))
        with open(self._fname, "w") as f:
            self._parser.write(f)


class JSONRequestHandler(web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def data_received(self, chunk):
        pass


class ApiUserOptionsHandler(JSONRequestHandler):
    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):
        self._options = kwargs.get("user_options")
        self._fn_on_save = kwargs.get("fn_on_save")

    def get(self):
        self._options.reload()
        self.write(json.dumps({s: self._options.get_options(s) for s in (self._options.list_sections())}))

    def post(self):
        data = json.loads(self.request.body)
        for section in data.keys():
            for key, value in data.get(section):
                self._options.set_option(section, key, value)
        if data:
            self._options.save()
            self._options.reload()
            self._fn_on_save()
        self.write(json.dumps(dict(message="ok")))


class JSONMethodDumpRequestHandler(JSONRequestHandler):
    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):
        self._method = kwargs.get("fn_method")

    def get(self):
        self.write(json.dumps(self._method()))


class NavigationRequestError(Exception):
    def __init__(self, *args, **kwargs):
        super(NavigationRequestError, self).__init__(args, kwargs)


class IllegalActionNavigationRequestError(Exception):
    def __init__(self, *args, **kwargs):
        super(IllegalActionNavigationRequestError, self).__init__(args, kwargs)


class UnknownRouteNavigationRequestError(Exception):
    def __init__(self, *args, **kwargs):
        super(UnknownRouteNavigationRequestError, self).__init__(args, kwargs)


class UnknownPointNavigationRequestError(Exception):
    def __init__(self, *args, **kwargs):
        super(UnknownPointNavigationRequestError, self).__init__(args, kwargs)


def delayed_open(store, route_name):
    if store.get_selected_route() != route_name:
        threading.Thread(target=store.open, args=(route_name,)).start()


class JSONNavigationHandler(JSONRequestHandler):
    # noinspection PyAttributeOutsideInit
    def initialize(self, **kwargs):
        self._store = kwargs.get("route_store")

    def get(self):
        action = self.get_query_argument("action")
        if action == "list":
            _routes = self._store.list_routes()
            _selected = self._store.get_selected_route()
            _response = {"routes": sorted(_routes), "selected": _selected}
            self.write(json.dumps(_response))
            threading.Thread(target=self._store.load_routes).start()
        else:
            self.write(json.dumps({}))

    def post(self):
        data = json.loads(self.request.body)
        action = data.get("action")
        selected_route = data.get("route")
        _active = len(self._store) > 0
        if action == "start" or (action == "toggle" and (not _active or self._store.get_selected_route() != selected_route)):
            delayed_open(self._store, selected_route)
        elif action in ("close", "toggle"):
            self._store.close()
        self.write(json.dumps(dict(message="ok")))


class GetSegmentSSID(tornado.web.RequestHandler):
    """Run a python script to get the SSID of current robot"""

    async def get(self):
        try:
            # Use the IOLoop to run fetch_ssid in a thread
            loop = tornado.ioloop.IOLoop.current()
            router = Router()

            # name of python function to run, ip of the router, ip of SSH, username, password, command to get the SSID
            ssid = await loop.run_in_executor(None, router.fetch_ssid)

            self.write(ssid)
        except Exception as e:
            logger.error(f"Error fetching SSID of current robot: {e}")
            self.set_status(500)
            self.write("Error fetching SSID of current robot.")
        self.finish()


class TemplateRenderer(tornado.web.RequestHandler):
    # Any static routes should be added here
    _TEMPLATES = {
        "nc": "index.html",
        "menu_controls": "userMenu/menu_controls.html",
        "menu_logbox": "userMenu/menu_logbox.html",
        "menu_settings": "userMenu/menu_settings.html",
        "mc": "mobile_controller_ui.html",
        "normal_ui": "normal_ui.html",
    }

    def initialize(self, page_name="nc"):
        self.page_name = page_name

    def get(self, page_name=None):  # Default to "nc" if no page_name is provided
        if page_name is None:
            page_name = self.page_name
        template_name = self._TEMPLATES.get(page_name)
        if template_name:
            self.render(f"../htm/templates/{template_name}")
        else:
            self.set_status(404)
            self.write("Page not found.")
