import zmq
import json
import threading, time
import logging
import configparser
import datetime
from pythonping import ping

from byodr.utils.ssh import Router, Nano

logger = logging.getLogger(__name__)


# This file will have the ZMQ socket and dealing with the robot configuration file


class DataPublisher(threading.Thread):
    def __init__(self, data, event, robot_config_dir, message=" ", sleep_time=5, pub_port=5454, rep_port=5455):
        super(DataPublisher, self).__init__()
        self.ip = Nano.get_ip_address()  # Replace with actual IP retrieval method
        self.json_data = data
        self.pub_port = pub_port
        self.rep_port = rep_port
        self.robot_config_dir = robot_config_dir
        self.message = message
        self.sleep_time = sleep_time
        self._quit_event = event

        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://{self.ip}:{self.pub_port}")
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://{self.ip}:{self.rep_port}")
        self.subscriber_ips = set()

    def run(self):
        try:
            while not self._quit_event.is_set():
                self.check_subscribers()
                robot_config_json_data = self.read_robot_config()
                # combined_message = f"{self.message} {json_data}"

                timestamp = datetime.datetime.now().isoformat()
                combined_message = f"{self.json_data}|{timestamp}"

                # print(f"Sent {combined_message}")
                self.pub_socket.send_string(combined_message)
                time.sleep(self.sleep_time)
        except Exception as e:
            logging.error(f"Exception in DataPublisher: {e}")
        finally:
            logging.info("DataPublisher is about to close")
            self.cleanup()

    def read_robot_config(self):
        # Read .ini file and process data
        config = configparser.ConfigParser()
        config.read(self.robot_config_dir)
        ini_data = {section: dict(config.items(section)) for section in config.sections()}
        return json.dumps(ini_data)

    def check_subscribers(self):
        try:
            notification = self.rep_socket.recv_string(zmq.NOBLOCK)
            action, subscriber_ip = notification.split()
            if action == "CONNECT":
                self.subscriber_ips.add(subscriber_ip)
                logger.info(f"Subscriber {subscriber_ip} connected")
            elif action == "DISCONNECT":
                self.subscriber_ips.discard(subscriber_ip)
                logger.info(f"Subscriber {subscriber_ip} disconnected")
            self.rep_socket.send(b"ACK")  # Acknowledge the subscriber
        except zmq.Again:
            pass  # No new subscriber or disconnection

    def cleanup(self):
        self.pub_socket.close()
        self.rep_socket.close()
        self.context.term()


import threading
import zmq
import json
import logging
import datetime, configparser
import os
import time

from byodr.utils.ssh import Router, Nano

# This file will have the ZMQ socket and dealing with the robot configuration file
logger = logging.getLogger(__name__)


class TeleopSubscriberThread(threading.Thread):
    def __init__(self, listening_ip, event, robot_config_dir, sub_port=5454, req_port=5455):
        # Set up necessary attributes and methods that TeleopSubscriberThread inherits from Thread.
        # Use the thread control methods like start(), join(), is_alive().
        super(TeleopSubscriberThread, self).__init__()
        self._listening_ip = listening_ip
        self._sub_port = sub_port
        self._req_port = req_port
        self._quit_event = event
        self.robot_config_dir = robot_config_dir
        self._robot_actions = RobotActions(self.robot_config_dir)

        self.context = zmq.Context()
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self._listening_ip}:{self._req_port}")

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{self._listening_ip}:{self._sub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.poller = zmq.Poller()
        self.poller.register(self.sub_socket, zmq.POLLIN)

    def run(self):
        subscriber_ip = Nano.get_ip_address()
        self.req_socket.send_string(f"CONNECT {subscriber_ip}")
        self.req_socket.recv()  # Wait for acknowledgement

        try:
            while not self._quit_event.is_set():
                socks = dict(self.poller.poll(1000))  # Check every 1000 ms
                if self.sub_socket in socks and socks[self.sub_socket] == zmq.POLLIN:
                    message = self.sub_socket.recv_string()
                    # print(message)
                    self.process_message(message)

        finally:
            self.req_socket.send_string(f"DISCONNECT {subscriber_ip}")
            logging.info("TeleopSubscriberThread is about to close")

            self.req_socket.recv()
            self.cleanup()

    def process_message(self, message):
        # it should check for difference here. if there is difference, then start router actions class and run the appropriate function from it
        received_time = datetime.datetime.now()
        received_json_data, timestamp = message.split("|")
        # Convert single quotes to double quotes for JSON parsing
        json_data_corrected = received_json_data.replace("'", '"')
        self._robot_actions.driver(json_data_corrected)

        try:
            # Manual parsing of the ISO format datetime string
            sent_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
            time_diff = received_time - sent_time
            # print(f"Time difference: {time_diff.total_seconds()} seconds")
        except ValueError:
            print("Invalid message format")

    def cleanup(self):
        self.sub_socket.close()
        self.req_socket.close()
        self.context.term()


class RouterActions:
class RobotActions:
    def __init__(self, robot_config):
        self.robot_config_dir = robot_config
        self._router = Router()
        # Retrieve the specific IP address
        self._ip = Nano.get_ip_address()
        self.received_json_data = None
        self.adjacent_segments = None
        self.current_segment = None
        self.current_segment_index = None

    def __set_parsers(self):
        #  Module reads data from INI files as strings. It doesn't matter if the data is int or bol
        self.robot_config_parser = configparser.ConfigParser()
        self.robot_config_parser.read(self.robot_config_dir)

    def driver(self, json_data):
        self.__set_parsers()
        # Parse the JSON data
        self.received_json_data = json.loads(json_data)
        # print(self.received_json_data)
        # Get segments from JSON and INI file
        self.json_segments = set(self.received_json_data.keys())
        self.ini_segments = set(self.robot_config_parser.sections())
        # Step 1: check if there are any changes between the received data and the existing one
        if self.check_for_difference():
            # logger.info("found difference")
            if self.check_segment_existence():
                self.router_visibility()
                # processed with the check for adjacent segment
                # DONE####
                # self.check_adjacent_segments()
                pass
            else:
                # remove the connection
                pass
            # self.default_robot_config()
        else:
            logger.info("No changes were found with all data in current robot_config.ini")

    def check_for_difference(self):
        """Check if there is a difference between received data and saved data in robot_config.ini"""
        # Initialize a flag to indicate if there is any difference
        is_different = False
        # Get segments from JSON and INI file
        self.json_segments = set(self.received_json_data.keys())
        self.ini_segments = set(self.robot_config_parser.sections())

        # Check each segment present in JSON data
        for segment in self.json_segments:
            # If segment is not in INI, it's a difference
            if segment not in self.ini_segments:
                is_different = True
                break

            # For existing segments, check each key
            for key in self.received_json_data[segment]:
                ini_value = self.robot_config_parser.get(segment, key, fallback="Key Not Found")
                json_value = self.received_json_data[segment][key]
                if str(ini_value) != str(json_value):
                    # logger.info(f"Difference found in {segment}: INI value '{ini_value}' vs JSON value '{json_value}'")
                    is_different = True
                    break

            if is_different:
                break

        return is_different

    def check_segment_existence(self):
        """Check if the current segment exists in the received data."""
        # should it check also if the data inside of it is the same as .ini file?
        for header, details in self.received_json_data.items():
            if details.get("ip.number") == self._ip:
                self.current_segment = details
                self.current_segment_index = int(header.replace("segment_", "")) - 1
                return True
        return False  # Return False if the current segment is not found

    # ADD FUNCTION TO CHECK FOR MAIN IN ROUTER VISIBILITY
    def router_visibility(self):
        current_state = self.current_segment.get("main")
        # self._router.change_wifi_visibility(current_state)

    def check_adjacent_segments(self):
        """
        Check for new, mismatched, and good segments in the adjacent segments.
        """
        # Identifying adjacent segments
        adjacent_segments_indices = [self.current_segment_index - 1, self.current_segment_index + 1]
        adjacent_segments = [f"segment_{i + 1}" for i in adjacent_segments_indices if i >= 0]

        # Consolidate .ini file data for comparison
        ini_data = {}
        for section in self.robot_config_parser.sections():
            if section.startswith("segment_"):
                ini_data[section] = {key: self.robot_config_parser.get(section, key) for key in ["ip.number", "wifi.name", "mac.address"]}

        for segment in adjacent_segments:
            json_segment_data = self.received_json_data.get(segment)

            if json_segment_data:
                # Check if the segment details exist in any .ini file segment
                # CASE FOR A NEW ADDED SEGMENT
                # Identify a segment as "new" if its details (IP, WiFi, MAC) in the JSON data do not exist under any header in the .ini file.
                if not any(json_segment_data == details for details in ini_data.values()):
                    logger.info(f"New segment: {json_segment_data.get('wifi.name')}")
                    # self.check_segment_connection(json_segment_data)
                    # Identify a segment as a "mismatch" if the same header exists in both JSON and .ini files but with different data.
                    # THIS IS THE CASE FOR REPOSITION FROM THE OP
                elif segment in ini_data and json_segment_data != ini_data[segment]:
                    # Mismatch in existing segment
                    logger.info(f"Mismatch in {segment}. JSON: {json_segment_data.get('wifi.name')}, INI: {ini_data[segment].get('wifi.name')}")
                    # self.check_segment_connection(json_segment_data)
                    # self.remove_segment_connection(ini_data[segment])
                elif segment in ini_data and json_segment_data == ini_data[segment]:
                    # Adjacent segment data matches
                    position = "before" if int(segment.split("_")[-1]) < self.current_segment_index + 1 else "after"
                    logger.info(f"Adjacent segment in position {position} is good")
                    # self.check_segment_connection(json_segment_data)

    def check_segment_connection(self, adjacent_segment):
        """Ping the adjacent segment to make sure there is both ways connection to it"""

        sleeping_time, connection_timeout_limit = 1, 5
        # print(adjacent_segment.get("ip.number"))
        adjacent_nano_ip = self._router.get_ip_from_mac(adjacent_segment.get("mac.address"))[1]
        while sleeping_time <= connection_timeout_limit:
            if self._router.check_network_connection(adjacent_nano_ip):
                logger.info(f"There is connection with {adjacent_segment.get('wifi.name')}. No action needed")
                # self.save_robot_config()
                break

            logger.info(f"Retrying in {sleeping_time} seconds ({sleeping_time}/{connection_timeout_limit})")
            time.sleep(sleeping_time)
            sleeping_time += 1

        # In a good day, this case shouldn't come true.
        if sleeping_time > connection_timeout_limit:
            logger.info(f"There is no connection with segment {adjacent_segment.get('wifi.name')}")
            logger.info("Will create connection with it")
            # self.create_segment_connection(adjacent_segment)

    def save_robot_config(self):
        """Delete the data existing in the current robot_config.ini and place all the received data in it"""
        # Saving the received data to the current robot_config.ini should be done only after the verification of segment existing
        # Which is done through check_segment_connection()
        logger.info("Saving received data to the current robot_config.ini")
        # Clear existing content in the configparser
        self.robot_config_parser.clear()

        # Iterate over the JSON data and add sections and keys to the INI file
        for segment, values in self.received_json_data.items():
            self.robot_config_parser.add_section(segment)
            for key, value in values.items():
                # Convert boolean strings 'true'/'false' to 'True'/'False'
                if isinstance(value, str) and value.lower() in ["true", "false"]:
                    value = value.capitalize()
                self.robot_config_parser.set(segment, key, value)

        # Write the updated configuration to the file
        with open(self.robot_config_dir, "w") as configfile:
            self.robot_config_parser.write(configfile)

    def remove_segment_connection(self, target_segment):
        adjacent_name = target_segment.get("wifi.name")
        logger.info(adjacent_name)
        # self._router.delete_network(adjacent_name)

    def create_segment_connection(self, target_segment):
        adjacent_name = target_segment.get("wifi.name")
        adjacent_mac = target_segment.get("mac.address")
        # logger.info(adjacent_name, adjacent_mac)
        # self._router.connect_to_network(adjacent_name, adjacent_mac)

    def default_robot_config(self):
        """Remove all the headers from current robot_config and rename the header of current's ip to be segment_1.
        Also, print the wifi.name of the segments before and after the matching segment (if they exist)."""
        # IT ISN"T FULLY WORKING YET
        # Read the current configuration
        config = configparser.ConfigParser()
        config.read(self.robot_config_dir)

        # Find the section with the matching IP address
        matching_section = None
        segments = [s for s in config.sections() if s.startswith("segment_")]
        for i, section in enumerate(segments):
            if config.get(section, "ip.number", fallback=None) == self._ip:
                matching_section = section
                matching_index = i
                break

        # Print WiFi names of segments before and after the matching segment
        if matching_section:
            section_data = {}
            if matching_index > 0:
                previous_section = segments[matching_index - 1]
                section_data["wifi.name"] = config.get(previous_section, "wifi.name", fallback="Not available")
                print(f"Lead segment WiFi name: {section_data['wifi.name']}")
                self.remove_segment_connection(section_data)
            if matching_index < len(segments) - 1:
                next_section = segments[matching_index + 1]
                section_data["wifi.name"] = config.get(next_section, "wifi.name", fallback="Not available")
                print(f"Follow segment WiFi name: {section_data['wifi.name']}")
                self.remove_segment_connection(section_data)

        #     # Store the details of the matching section
        #     details = dict(config.items(matching_section))

        #     # Remove all segment_ sections
        #     for section in segments:
        #         config.remove_section(section)

        #     # Add the matching section back as segment_1
        #     config["segment_1"] = details

        #     # Write the updated configuration back to the file
        #     with open(self.robot_config_dir, "w") as configfile:
        #         config.write(configfile)
        #     logger.info("Removed all sections from current robot_config")
        # else:
        #     logger.info("No matching section found.")

    # def compare_segments(self, adjacent_segment, position):
    #     """Compare the data received with the existing one in robot_config for only the adjacent segments"""

    #     # Check if the adjacent segment exists in the INI file
    #     if adjacent_segment not in self.robot_config_parser:
    #         logger.info(f"New header's details for {position} segment is {adjacent_segment}")
    #         return
    #     # IN CASE THE SEGMENT'S KEY_TO_COMPARE IS NEW, AND THERE WASN'T A HEADER IN THE SAME NAME AS IT IN THE .INI FILE, THEN LOG "GOT A NEW SEGMENT THAT DIDN'T EXIST BEFORE" AND PRINT IT'S WIFI.NAME.
    #     # IF THE SEGMENT'S KEY_TO_COMPARE IS NEW, AND THERE WAS A HEADER IN THE SAME NAME AS IT IN THE .INI FILE, THEN
    #     # 1- LOG "DELETING OLD CONNECTION" AND PRINT THE OLD SEGMENT'S (THE ONE FROM .INI FILE) WIFI.NAME
    #     # 3- PRINT "MAKING NEW CONNECTION" AND PRINT THE NEW SEGMENT'S (IN JSON DATA) WIFI.NAME AND MAC.ADDRESS
    #     #  DELETE THE OLD CONNECTION FROM THE SAME POSITION IN .INI FILE AND MAKE NEW CONNECTION WITH THE ONE RECEIVED FROM THE JSON
    #     # Define the keys to compare. The v.number can be added later
    #     keys_to_compare = ["ip.number", "wifi.name", "mac.address"]
    #     ini_segment_data = {key: self.robot_config_parser.get(adjacent_segment, key) for key in keys_to_compare}
    #     json_segment_data = self.received_json_data.get(adjacent_segment, {})

    #     # Check if all required keys are present in JSON data
    #     if all(key in json_segment_data for key in keys_to_compare):
    #         # Check if all data is different
    #         if all(json_segment_data.get(key) != ini_segment_data.get(key) for key in keys_to_compare):
    #             logger.info(f"Got new segment in {position} position")
    #         # Check for change in IP address only
    #         elif json_segment_data.get("ip.number") != ini_segment_data.get("ip.number"):
    #             logger.info("Change in the position of adjacent segment")
    #             # self.remove_segment_connection(adjacent_segment)
    #         # If no change in specified keys
    #         else:
    #             self.check_segment_connection(position, adjacent_segment)
    #     else:
    #         logger.info(f"Not all required keys found in JSON data for {position} segment {adjacent_segment}")

    #     # Additional checks or actions can be added here if needed

    # DEALING WITH THE NETWORK
    # def check_adjacent_segments(self):
    #     # Check if there are segments that are after or before the current one with the .ini file
    #     # 1-I will give you an ip.number for the current entry in the json data, let's say it is self._ip.
    #     # 2-you should compare the data between the json and .ini file with between the current segment and the entry after or before it only.
    #     # 3-if there is a new adjacent segment then print (new header's {DETAILS})
    #     # 4-if the after and before entry are the same, then check the data in them
    #     # you can decide if you want to make the two checks (point 3 and 4) inside each others or each alone. It is up to you
    #     # if the data for after or before is changed then print (changed data in {AFTER OR BEFORE}  is {KEY AND VALUE OF CHANGED DATA FROM THE INI FILE})
    #     pass
