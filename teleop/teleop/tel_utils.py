import concurrent.futures
import configparser
import glob
import logging
import os
import threading
import time
from datetime import datetime

import folium
import pandas as pd
import tornado.ioloop
import tornado.web
import user_agents  # Check in the request header if it is a phone or not
from byodr.utils import timestamp
from byodr.utils.ssh import Router

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
        offline_dep = self.use_local_files(content)  # Ensure this method is defined to handle local file dependencies

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

    def throttle_control(self, cmd):
        """Function used to smooth out the received throttle from front-end. Instead of going from a full throttle of 1 to 0, it will decrease gradually by 0.05.

        Args:
            cmd JSON: The json sent from the front-end. Example `{"steering": 0.0, "throttle": 0.5, "time": 1717055030186955, "navigator": {"route": None}, "button_b": 1}`
        """
        # Check if there is no smoothing required for mobile inference states
        if cmd.get("mobileInferenceState") in ["true", "auto", "train"]:
            self.teleop_publish(cmd)
            return

        # If no throttle or steering key present in the command, reset throttle to 0
        if "throttle" not in cmd and "steering" not in cmd:
            self.current_throttle = 0
            self.teleop_publish({"steering": 0.0, "throttle": 0, "time": timestamp(), "navigator": {"route": None}, "button_b": 1})
            return

        target_throttle = float(cmd.get("throttle", 0))

        if "throttle" in cmd:
            # Smooth the throttle change
            if abs(target_throttle - self.current_throttle) > self.throttle_change_step:
                # Determine the direction of change
                throttle_direction = (target_throttle - self.current_throttle) / abs(target_throttle - self.current_throttle)
                self.current_throttle += throttle_direction * self.throttle_change_step
                # Ensure we don't overshoot the target throttle
                if (throttle_direction > 0 and self.current_throttle > target_throttle) or (throttle_direction < 0 and self.current_throttle < target_throttle):
                    self.current_throttle = target_throttle
            else:
                self.current_throttle = target_throttle

        cmd["throttle"] = self.current_throttle
        self.teleop_publish(cmd)

    def teleop_publish(self, cmd):
        # We are the authority on route state.
        cmd["navigator"] = dict(route=self.route_store.get_selected_route())
        self.teleop_publisher.publish(cmd)


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


class DirectingUser(tornado.web.RequestHandler):
    """Directing the user based on their used device"""

    def get(self):
        user_agent_str = self.request.headers.get("User-Agent")
        user_agent = user_agents.parse(user_agent_str)

        if user_agent.is_mobile:
            # if user is on mobile, redirect to the mobile page
            logger.info("User is operating through mobile phone. Redirecting to the mobile UI")
            self.redirect("/mc")
        else:
            # else redirect to normal control page
            self.redirect("/nc")


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
