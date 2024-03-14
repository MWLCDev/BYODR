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

    def record_gps(self):
        try:
            while self.running:
                messages = self.vehicle.get()
                for message in messages:
                    latitude_geo = message.get("latitude_geo")
                    longitude_geo = message.get("longitude_geo")
                    time_geo = message.get("time")
                    if latitude_geo is not None and longitude_geo is not None:
                        self.geo_location.append([latitude_geo, longitude_geo, time_geo])
        except Exception as e:
            logger.error(f"Error collecting data: {e}")


    # WOULD NEED TO MERGE THE DATA ALL. THEN CLEAN THEM IN A WAY THAT THERE WON'T BE A BIG GAP BETWEEN THE LONGITUDE AND LATITUDE SO THERE ISN'T GAP IN THE LINE
    # add data that is only similar in the time
    # is there a way to clean it to a limit?
    # it needs to remove with the x axis
    # merge the lists first and then convert the merged list to a NumPy array
    def merge_data_array(self):
        merged_list = [[s, geo] for s, geo in zip(self.steer_confidences, self.geo_location)]
        merged_array = np.array(merged_list)
        merged_array = np.around(merged_array, decimals=5)

    # make if condition if the value of gps is zero
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
