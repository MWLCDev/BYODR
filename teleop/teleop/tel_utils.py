import threading
import logging
import time
import numpy as np

logger = logging.getLogger(__name__)


class OverviewConfidence:
    def __init__(self, inference, vehicle):
        self.inference = inference
        self.vehicle = vehicle
        self.running = False
        self.threads = []
        self.steer_confidences = []
        self.geo_location = []
        self.merged_data = []


    def record_confidence(self):
        try:
            while self.running:
                messages = self.inference.get()
                # inference sends a message as list with 20 entries inside
                for message in messages:
                    steer_confidence = message.get("steer_confidence")
                    steer_confidence_time = message.get("time")
                    if steer_confidence is not None:
                        self.steer_confidences.append([steer_confidence, steer_confidence_time])
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
