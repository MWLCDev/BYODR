import collections
import glob
import logging
import multiprocessing
import os
import threading
import time
from datetime import datetime

import folium
import numpy as np
import pandas as pd

# needs to be installed on the router
from pysnmp.hlapi import *

logger = logging.getLogger(__name__)


class OverviewConfidence:
    def __init__(self, inference, vehicle, rut_gps_poller):
        self.inference = inference
        self.vehicle = vehicle
        self.running = False
        self.merged_list = []
        self.cleaned_list = []
        self.coloured_list = []
        self.rut_gps_poller = rut_gps_poller
        self.sleep_time = 0.2

    def record_data(self):
        """Get confidence from inference socket and long, lat from vehicle socket then store them in a variable"""
        try:
            while self.running:
                inference_messages = self.inference.get()
                for inf_message in inference_messages:
                    # Process paired messages
                    steer_confidence = inf_message.get("steer_confidence")
                    latitude = self.rut_gps_poller.get_latitude()
                    longitude = self.rut_gps_poller.get_longitude()
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


class GpsPollerThreadSNMP(threading.Thread):
    """
    A thread class that continuously polls GPS coordinates using SNMP and stores
    the latest value in a queue. It can be used to retrieve the most recent GPS
    coordinates that the SNMP-enabled device has reported.
    https://wiki.teltonika-networks.com/view/RUT955_SNMP

    Attributes:
        _host (str): IP address of the SNMP-enabled device (e.g., router).
        _community (str): SNMP community string for authentication.
        _port (int): Port number where SNMP requests will be sent.
        _quit_event (threading.Event): Event signal to stop the thread.
        _queue (collections.deque): Thread-safe queue storing the latest GPS data.
    Methods:
        quit: Signals the thread to stop running.
        get_latitude: Retrieves the latest latitude from the queue.
        get_longitude: Retrieves the latest longitude from the queue.
        fetch_gps_coordinates: Fetches GPS coordinates from the SNMP device.
        run: Continuously polls for GPS coordinates until the thread is stopped.
    """

    # There was alternative solution with making a post request and fetch a new token https://wiki.teltonika-networks.com/view/Monitoring_via_JSON-RPC_windows_RutOS#GPS_Data
    def __init__(self, host, community="public", port=161):
        super(GpsPollerThreadSNMP, self).__init__()
        self._host = host
        self._community = community
        self._port = port
        self._quit_event = threading.Event()
        self._queue = collections.deque(maxlen=1)

    def quit(self):
        self._quit_event.set()

    def get_latitude(self, default=0.0):
        """
        Args:
            default (float): The default value to return if the queue is empty. Defaults to 0.0.

        Returns:
            float: The latest latitude value, or the default value if no data is available.
        """
        return self._queue[0][0] if len(self._queue) > 0 else default

    def get_longitude(self, default=0.0):
        return self._queue[0][1] if len(self._queue) > 0 else default

    def fetch_gps_coordinates(self):
        """
        Sends an SNMP request to the device to retrieve the current
        latitude and longitude values. If successful, the values are returned.

        Returns:
            tuple: A tuple containing the latitude and longitude as floats, or `None` if the request fails.
        """
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(self._community, mpModel=1),
            UdpTransportTarget((self._host, self._port)),
            ContextData(),
            ObjectType(ObjectIdentity(".1.3.6.1.4.1.48690.3.1.0")),  # GPS Latitude
            ObjectType(ObjectIdentity(".1.3.6.1.4.1.48690.3.2.0")),  # GPS Longitude
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            logger.error(f"Error: {errorIndication}")
            return None
        elif errorStatus:
            logger.error(f"Error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}")
            return None
        else:
            latitude, longitude = [float(varBind[1]) for varBind in varBinds]
            return latitude, longitude

    def run(self):
        """
        The main method of the thread that runs continuously until the quit event is set.
        """
        while not self._quit_event.is_set():
            try:
                coordinates = self.fetch_gps_coordinates()
                if coordinates:
                    self._queue.appendleft(coordinates)
                    # logger.info(f"Latitude: {coordinates[0]}, Longitude: {coordinates[1]}")
                    time.sleep(0.100)  # Interval for polling
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                time.sleep(10)
