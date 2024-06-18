import glob
import logging
import os
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import configparser, queue


import folium
import pandas as pd
import requests
from byodr.utils import timestamp

# needs to be installed on the router
from pysnmp.hlapi import *
from requests.auth import HTTPDigestAuth


logger = logging.getLogger(__name__)


class OverviewConfidence:
    def __init__(self, inference, vehicle):
        self.inference = inference
        self.vehicle = vehicle
        self.running = False
        self.merged_list = []
        self.cleaned_list = []
        self.coloured_list = []
        self.sleep_time = 0.2

    def record_data(self):
        """Get confidence from inference socket and long, lat from vehicle socket then store them in a variable"""
        try:
            while self.running:
                inference_messages = self.inference.get()
                vehicle_messages = self.vehicle.get()
                # Use zip to iterate over both lists simultaneously.
                for inf_message, veh_message in zip(inference_messages, vehicle_messages):
                    steer_confidence = inf_message.get("steer_confidence")
                    latitude = veh_message.get("latitude_geo")
                    longitude = veh_message.get("longitude_geo")
                    # Check if all required data is present before appending.
                    if steer_confidence is not None and latitude is not None and longitude is not None:
                        self.merged_list.append([round(steer_confidence, 5), latitude, longitude])
                        time.sleep(self.sleep_time)
        except Exception as e:
            logger.error(f"Error collecting data: {e}")

    def process_data(self):
        self.cleaned_list = self.clean_list(self.merged_list)
        self.coloured_list = self.assign_colors(self.cleaned_list)
        self.plot_data_on_map(self.coloured_list)

    def clean_list(self, list_to_clean):
        """Cleans a list of [confidence, longitude, latitude] by dropping 'confidence' duplicates."""
        try:

            # Convert to DataFrame
            df = pd.DataFrame(list_to_clean, columns=["Confidence", "Latitude", "Longitude"])

            # Drop duplicates based on the 'Confidence' column
            cleaned_df = df.drop_duplicates(subset=["Confidence"])
            cleaned_list = cleaned_df.values.tolist()
            return cleaned_list
        except Exception as e:
            logger.error(f"An error occurred: {e}")

    def assign_colors(self, assign_colours_list):
        """
        Process the input data to assign colors based on confidence levels.
        Each data point will be transformed to [confidence, longitude, latitude, color].
        Args:
        - data (list): List of data points [confidence, lat, lon].

        Returns:
        - list: List of processed data points [confidence, lon, lat, color].
        """
        processed_data = []
        for confidence, lat, lon in assign_colours_list:
            if confidence <= 0.25:
                color = "darkred"
            elif confidence <= 0.50:
                color = "lightred"
            elif confidence <= 0.75:
                color = "orange"
            else:
                color = "green"

            processed_data.append([confidence, lon, lat, color])
        return processed_data

    def clean_directory(self, base_folder):
        """
        Delete all .html files in the specified directory.
        """
        for file_path in glob.glob(os.path.join(base_folder, "*.html")):
            try:
                os.remove(file_path)
                logger.info(f"Deleted old map file: {file_path}")
            except OSError as e:
                logger.info(f"Error deleting file {file_path}: {e}")

    # store the output with and without the cleaning
    def plot_data_on_map(self, list_to_plot, base_folder="./htm/overview_confidence"):
        """
        Plot the processed data on a map with a continuous line where each segment has the color of the starting point.
        The processed data should have the structure [confidence, longitude, latitude, color].
        """
        self.clean_directory(base_folder)
        current_time = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        # Create the directory structure
        os.makedirs(base_folder, exist_ok=True)
        file_name = f"{current_time}map.html"
        file_path = os.path.join(base_folder, file_name)
        self.debug_data(list_to_plot, current_time, base_folder)

        # Create a map centered at an average location
        average_lat = sum(item[2] for item in list_to_plot) / len(list_to_plot)
        average_lon = sum(item[1] for item in list_to_plot) / len(list_to_plot)
        m = folium.Map(location=[average_lat, average_lon], zoom_start=12, max_zoom=25)

        # Draw a line for each segment with the color of the starting point
        for i in range(len(list_to_plot) - 1):
            _, lon1, lat1, color = list_to_plot[i]
            _, lon2, lat2, _ = list_to_plot[i + 1]
            folium.PolyLine([(lat1, lon1), (lat2, lon2)], color=color, weight=2.5, opacity=1).add_to(m)

        # Save the map to an HTML file
        m.save(file_path)
        with open(file_path, "r") as file:
            content = file.read()
            # Ensure this method is defined to handle local file dependencies
        offline_dep = self.use_local_files(content)

        with open(file_path, "w") as file:
            file.write(offline_dep)

        self.map_name = file_name

    def debug_data(self, data_to_debug, current_time, base_folder):
        file_name_txt = f"{current_time}coordinates.txt"
        file_path_txt = os.path.join(base_folder, file_name_txt)
        # Save coordinates and confidence to a txt file
        with open(file_path_txt, "w") as file_txt:
            file_txt.write(f"Sleep time : {self.sleep_time}\n")
            for item in data_to_debug:
                # print(item)
                file_txt.write(f"Confidence: {item[0]}, Longitude: {item[1]}, Latitude: {item[2]}, Color: {item[3]}\n")

            # Optionally, write non-cleaned data
            file_txt.write("\nNon-cleaned data:\n")
            for item in self.merged_list:
                file_txt.write(f"{item}\n")

    def use_local_files(self, content):
        """Replace online src attributes with local file paths"""
        content = content.replace("https://cdn.jsdelivr.net/npm/leaflet@1.6.0/dist/leaflet.js", "/static/external/leaflet.js")
        content = content.replace("https://code.jquery.com/jquery-1.12.4.min.js", "/static/external/jquery-1.12.4.min.js")
        content = content.replace("https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js", "/static/external/bootstrap.min.js")
        content = content.replace("https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js", "/static/external/leaflet.awesome-markers.js")
        content = content.replace("https://cdn.jsdelivr.net/npm/leaflet@1.6.0/dist/leaflet.css", "/static/external/leaflet.css")
        content = content.replace("https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css", "/static/external/bootstrap.min.css")
        content = content.replace("https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap-theme.min.css", "/static/external/bootstrap-theme.min.css")
        content = content.replace("https://maxcdn.bootstrapcdn.com/font-awesome/4.6.3/css/font-awesome.min.css", "/static/external/font-awesome.min.css")
        content = content.replace("https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css", "/static/external/leaflet.awesome-markers.css")
        content = content.replace("https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css", "/static/external/leaflet.awesome.rotate.min.css")
        return content

    def start(self):
        """Start the thread and clear the merged data lists"""
        if not self.running:
            self.running = True
            self.merged_list = []
            self.record_data_thread = threading.Thread(target=self.record_data)
            self.record_data_thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.record_data_thread.join()


class ThrottleController:
    def __init__(self, teleop_publisher, route_store):
        self.current_throttle = 0.0
        self.throttle_change_step = 0.05
        self.teleop_publisher = teleop_publisher
        self.route_store = route_store
        self.command_queue = queue.Queue()
        self.following_state = "inactive"

        # Start the thread to consume from the queue
        # The main thread can be used to run this function, but I would leave the main thread free
        threading.Thread(target=self.consume_queue, daemon=True).start()

    def throttle_control(self, cmd):
        """Enqueue moving commands instead of processing directly"""
        self.command_queue.put(cmd)

    def consume_queue(self):
        """Continuously consumes commands from the queue and processes them."""
        while True:
            try:
                cmd = self.command_queue.get(block=True)
                if self.following_state == "active":
                    if cmd.get("source") == "followingActive":
                        self._process_command(cmd)
                    else:
                        pass
                        # Can be used to save the commands from other sources then process them later
                        # self.command_queue.put(cmd)
                else:
                    self._process_command(cmd)
            except Exception as e:
                logger.error(f"Error processing command from queue: {e}")

    def _process_command(self, cmd):
        """Processes a command from the queue, smoothing the throttle changes if necessary."""
        if cmd.get("mobileInferenceState") in ["true", "auto", "train"] or cmd.get("source") in ["followingActive"]:
            self._teleop_publish(cmd)
            return

        if "throttle" not in cmd and "steering" not in cmd:
            self.current_throttle = 0
            self._teleop_publish({"steering": 0.0, "throttle": 0, "time": timestamp(), "navigator": {"route": None}, "button_b": 1})
            return

        target_throttle = float(cmd.get("throttle", 0))

        if "throttle" in cmd:
            if abs(target_throttle - self.current_throttle) > self.throttle_change_step:
                throttle_direction = (target_throttle - self.current_throttle) / abs(target_throttle - self.current_throttle)
                self.current_throttle += throttle_direction * self.throttle_change_step
                if (throttle_direction > 0 and self.current_throttle > target_throttle) or (throttle_direction < 0 and self.current_throttle < target_throttle):
                    self.current_throttle = target_throttle
            else:
                self.current_throttle = target_throttle

        cmd["throttle"] = self.current_throttle
        self._teleop_publish(cmd)

    def _teleop_publish(self, cmd):
        """Private function which shouldn't be called directly"""
        cmd["navigator"] = dict(route=self.route_store.get_selected_route())
        # logger.info(cmd)
        self.teleop_publisher.publish(cmd)

    def update_following_state(self, state):
        self.following_state = state


class EndpointHandlers:
    """Functions that are used as parameters for the endpoint handlers in tornado."""

    def __init__(self, tel_application, tel_chatter, zm_client, route_store):
        self.tel_application = tel_application
        self.tel_chatter = tel_chatter
        self.zm_client = zm_client
        self.route_store = route_store

    def on_options_save(self):
        self.tel_chatter.publish(dict(time=timestamp(), command="restart"))
        self.tel_application.setup()

    def list_process_start_messages(self):
        return self.zm_client.call(dict(request="system/startup/list"))

    def list_service_capabilities(self):
        return self.zm_client.call(dict(request="system/service/capabilities"))

    def get_navigation_image(self, image_id):
        return self.route_store.get_image(image_id)


class CameraControl:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user = user
        self.password = password
        self.lock = threading.Lock()  # Initialize a lock for camera control

    def adjust_ptz(self, pan=None, tilt=None, panSpeed=100, tiltSpeed=100, duration=500, method="Continuous"):
        try:
            if method == "Momentary":
                url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/Momentary"
                payload = f"<PTZData><pan>{pan}</pan><tilt>{tilt}</tilt><panSpeed>{panSpeed}</panSpeed><tiltSpeed>{tiltSpeed}</tiltSpeed><zoom>0</zoom><Momentary><duration>{duration}</duration></Momentary></PTZData>"
            elif method == "Continuous":
                url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/Continuous"
                payload = f"<PTZData><pan>{pan}</pan><tilt>{tilt}</tilt><panSpeed>{panSpeed}</panSpeed><tiltSpeed>{tiltSpeed}</tiltSpeed><zoom>0</zoom><Continuous><duration>{duration}</duration></Continuous></PTZData>"
            elif method == "Absolute":
                url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/Absolute"
                payload = (
                    "<PTZData>"
                    f"<AbsoluteHigh><azimuth>{pan}</azimuth><elevation>{tilt}</elevation><panSpeed>{panSpeed}</panSpeed><tiltSpeed>{tiltSpeed}</tiltSpeed><absoluteZoom>10</absoluteZoom></AbsoluteHigh>"
                    "</PTZData>"
                )

            response = requests.put(url, auth=HTTPDigestAuth(self.user, self.password), data=payload, headers={"Content-Type": "application/xml"})
            if response.status_code == 200:
                return "Success: PTZ adjusted."
            else:
                logger.info(f"Error: Unexpected response {response.status_code} - {response.text}")
                return f"Error: Unexpected response {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as err:
            return f"Error: {err}"

    def get_ptz_status(self):
        url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/status"
        try:
            response = requests.get(url, auth=HTTPDigestAuth(self.user, self.password))
            response.raise_for_status()
            xml_root = ET.fromstring(response.content)
            ns = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}
            azimuth = xml_root.find(".//hik:azimuth", ns).text
            elevation = xml_root.find(".//hik:elevation", ns).text
            return (azimuth, elevation)
        except requests.exceptions.RequestException as e:
            return f"Failed to get PTZ status: {e}"
        except ET.ParseError as e:
            return f"XML parsing error: {e}"

    def set_home_position(self):
        url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/homeposition/set"
        response = requests.put(url, auth=HTTPDigestAuth(self.user, self.password))
        try:
            response.raise_for_status()
            return "Success: Home position set."
        except requests.exceptions.HTTPError as err:
            return f"Error: {err}"

    def goto_home_position(self):
        url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/homeposition/goto"
        response = requests.put(url, auth=HTTPDigestAuth(self.user, self.password))
        try:
            response.raise_for_status()
            if response.status_code == 200:
                return "Success: Camera moved to Home position."
            else:
                logger.info(f"Error: Unexpected response {response.status_code} - {response.text}")
                return f"Error: Unexpected response {response.status_code} - {response.text}"
        except requests.exceptions.HTTPError as err:
            return f"Error: {err}"

    def set_preset_position(self, preset_id):
        """Sets the current position of the PTZ camera as a preset position."""
        url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/presets/{preset_id}"
        payload = f"<PTZPreset><id>{preset_id}</id><presetName>Preset{preset_id}</presetName></PTZPreset>"
        response = requests.put(url, auth=HTTPDigestAuth(self.user, self.password), data=payload, headers={"Content-Type": "application/xml"})
        try:
            response.raise_for_status()
            if response.status_code == 200:
                return f"Success: Preset position {preset_id} set."
            else:
                logger.info(f"Error: Unexpected response {response.status_code} - {response.text}")
                return f"Error: Unexpected response {response.status_code} - {response.text}"
        except requests.exceptions.HTTPError as err:
            return f"Error: {err}"

    def goto_preset_position(self, preset_id):
        """Moves the PTZ camera to a specific preset position."""
        url = f"{self.base_url}/ISAPI/PTZCtrl/channels/1/presets/{preset_id}/goto"
        response = requests.put(url, auth=HTTPDigestAuth(self.user, self.password), headers={"Content-Type": "application/xml"})
        try:
            response.raise_for_status()
            if response.status_code == 200:
                logger.info(f"went to preset {preset_id}")
                return f"Success: Camera moved to preset position {preset_id}."
            else:
                logger.info(f"Error: Unexpected response {response.status_code} - {response.text}")
                return f"Error: Unexpected response {response.status_code} - {response.text}"
        except requests.exceptions.HTTPError as err:
            return f"Error: {err}"


class FollowingUtils:
    def __init__(self, tel_chatter, throttle_controller, fol_comm_socket):
        self.tel_chatter = tel_chatter
        self.throttle_controller = throttle_controller
        self.following_socket = fol_comm_socket
        self.following_state = "loading"
        self.camera_control = None

    def configs(self, user_config_file_dir):
        config = configparser.SafeConfigParser()
        config.read(user_config_file_dir)
        front_camera_ip = config.get("camera", "front.camera.ip", fallback="192.168.1.64")
        self.camera_control = CameraControl(f"http://{front_camera_ip}:80", "user1", "HaikuPlot876")

    def get_following_state(self):
        return self.following_state

    def set_following_state(self, new_state):
        self.following_state = new_state
        self.throttle_controller.update_following_state(new_state)

    def process_socket_commands(self):
        try:
            ctrl = self.following_socket.get()
            # logger.info(ctrl)
            if ctrl is not None:
                ctrl["time"] = int(timestamp())
                self.throttle_controller.throttle_control(ctrl)
                self._update_following_status(ctrl)
                self._handle_camera_commands(ctrl)
                self._publish_camera_azimuth()
        except Exception as e:
            logger.error(f"Error handling control command: {e}")

    def _update_following_status(self, ctrl):
        # There can be more than one source for the commands to TEL. That is why the sent value, is different from the ones stored as following_state
        if ctrl["source"] == "followingLoading":
            self.set_following_state("loading")
        elif ctrl["source"] == "followingInactive":
            self.set_following_state("inactive")
        elif ctrl["source"] == "followingActive":
            self.set_following_state("active")

    def _handle_camera_commands(self, ctrl):
        if "camera_pan" in ctrl:
            try:
                if isinstance(ctrl["camera_pan"], int):
                    self.camera_control.adjust_ptz(pan=ctrl["camera_pan"], tilt=0, method="Momentary")
                elif ctrl["camera_pan"] == "go_preset_1":
                    self.camera_control.goto_preset_position(preset_id=1)
            except Exception as cam_err:
                logger.error(f"Error in camera control: {cam_err}")

    def _publish_camera_azimuth(self):
        try:
            camera_azimuth, _ = self.camera_control.get_ptz_status()
            self.tel_chatter.publish({"camera_azimuth": camera_azimuth})
        except Exception as e:
            logger.error(f"Error publishing camera azimuth: {e}")

    def teleop_publish_to_following(self, cmd):
        try:
            self.tel_chatter.publish(cmd)
        except Exception as e:
            logger.error(f"Exception in teleop_publish_to_following: {e}")
