import threading
import logging
import time
import numpy as np

logger = logging.getLogger(__name__)


class OverviewConfidence:
    def __init__(self, inference, vehicle, rut_gps_poller):
        self.inference = inference
        self.vehicle = vehicle
        self.running = False
        self.merged_data = []
        self.cleaned_data = []
        self.rut_gps_poller = rut_gps_poller

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
                        self.merged_data.append([round(steer_confidence, 5), latitude, longitude])
                    # logger.info(self.merged_data[:-1])
                    # time.sleep(1)
        except Exception as e:
            logger.error(f"Error collecting data: {e}")

    def clean_list(self):
        """
        Cleans merged_data [confidence, longitude, latitude] by removing duplicates based on the confidence value
        """
        try:
            # Convert merged_data into a DataFrame
            df = pd.DataFrame(self.merged_data, columns=["confidence", "longitude", "latitude"])

            # Sort by 'confidence' in descending order to ensure the highest confidence entry is retained after dropping duplicates
            df_sorted = df.sort_values("confidence", ascending=False)

            # Drop duplicates based on 'longitude' and 'latitude', keeping the first entry (highest confidence due to sort)
            df_cleaned = df_sorted.drop_duplicates(subset=["longitude", "latitude"], keep="first")

            # Convert the cleaned DataFrame back into a list
            self.cleaned_data = df_cleaned.values.tolist()

        except Exception as e:
            logger.error(f"An error occurred: {e}")

    def process_data_and_assign_colors(self):
        """
        Process the input data to assign colors based on confidence levels.
        Each data point will be transformed to [confidence, longitude, latitude, color].
        Args:
        - data (list): List of data points [confidence, lat, lon].

        Returns:
        - list: List of processed data points [confidence, lon, lat, color].
        """
        processed_data = []
        for confidence, lat, lon in self.cleaned_data:
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

    # delete it after the user clicks on view
    def plot_data_on_map(self, base_folder="./htm/overview_confidence"):
        """
        Plot the processed data on a map and save it as an HTML file.
        The processed data should have the structure [confidence, longitude, latitude, color].
        Args:
        - processed_data (list): List of processed data points.
        - file_name (str): Name of the HTML file to save the map.
        """
        self.cleaned_data = self.process_data_and_assign_colors()
        current_time = datetime.now().strftime("%Y-%m-%dT%H%M%S")
        # Create the directory structure
        os.makedirs(base_folder, exist_ok=True)
        file_name = f"{current_time}map.html"
        file_path = os.path.join(base_folder, file_name)

        # Create a map centered at an average location
        average_lat = sum(item[2] for item in self.cleaned_data) / len(self.cleaned_data)
        average_lon = sum(item[1] for item in self.cleaned_data) / len(self.cleaned_data)
        m = folium.Map(location=[average_lat, average_lon], zoom_start=12, max_zoom=22)
        # be able to zoom more into the view

        bounds = []
        # Plot each point and extend bounds
        for _, lon, lat, color in self.cleaned_data:
            folium.CircleMarker(location=[lat, lon], radius=5, color=color, fill=True, fill_color=color).add_to(m)
            bounds.append([lat, lon])

        # Fit map to bounds if not empty
        if bounds:
            m.fit_bounds(bounds)

        # Save the map to an HTML file
        m.save(file_path)
        with open(file_path, "r") as file:
            content = file.read()
        offline_dep = self.use_local_files(content)

        with open(file_path, "w") as file:
            file.write(offline_dep)

        self.map_name = file_name

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
        if not self.running:
            self.running = True
            self.steer_confidences = []
            self.geo_location = []
            self.record_data_thread = threading.Thread(target=self.record_data)
            # self.record_gps_thread = threading.Thread(target=self.record_gps)
            self.threads = [self.record_data_thread]
            [t.start() for t in self.threads]

    def stop(self):
        if self.running:
            self.running = False
            [t.join() for t in self.threads]

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
