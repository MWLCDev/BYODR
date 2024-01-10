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
                combined_message = f"{self.json_data}|{self.message}|{timestamp}"

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
        self._router = Router()
        self._router_actions = RouterActions()

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
                    # print(f"Received: {message}")
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
        self._router_actions.driver(json_data_corrected)
            self._router_actions.add_connection(json_data_corrected)
        try:
            # Manual parsing of the ISO format datetime string
            sent_time = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
            time_diff = received_time - sent_time
            # print(f"Time difference: {time_diff.total_seconds()} seconds")

            # if action_command == "Add":
            #     print("1")
            # elif action_command == "Remove":
            #     print("2")
            # elif action_command == "Reposition":
            #     print("3")
        except ValueError:
            print("Invalid message format")

    def format_segment_details(self, segment, details_dict):
        return f"{segment}: " + ", ".join(f"{key} = {value}" for key, value in details_dict.items())

    def output_differences(self, json_data):
        # Convert single quotes to double quotes for JSON parsing

        # Parse the JSON data
        json_dict = json.loads(json_data)

        # Read and parse the INI file
        config = configparser.ConfigParser()
        with open(self.robot_config_dir, "r") as ini_file:
            config.read_file(ini_file)

        json_segments = set(json_dict.keys())
        ini_segments = set(config.sections())

        if json_segments > ini_segments:
            extra_segments = json_segments - ini_segments
            for segment in extra_segments:
                print(f"Adding more sections: {segment} ==> " + ", ".join(f"{key} = {value}" for key, value in json_dict[segment].items()))
        elif json_segments < ini_segments:
            extra_segments = ini_segments - json_segments
            for segment in extra_segments:
                # Convert the configparser section to a dictionary
                segment_details = {key: config[segment][key] for key in config[segment]}
                print(f"ٌRemoving sections: {segment} ==> " + ", ".join(f"{key} = {value}" for key, value in segment_details.items()))
        else:
            print("No difference in sections")

    def cleanup(self):
        self.sub_socket.close()
        self.req_socket.close()
        self.context.term()


class RouterActions:
    def add_connection(self, json_data):
        # Convert JSON data to a dictionary if it's in string format
        self_ip = Nano.get_ip_address()
        data = json.loads(json_data)
        # Extract headers and their respective data
        headers = list(data.keys())
        found = False
        for i, header in enumerate(headers):
            if data[header]["ip.number"] == self_ip:
                found = True
                # This case wouldn't happen, as the message would have at least two segments in it.
                if len(headers) == 1:
                    # Isolated segment
                    print(f"Self IP found in {header}. No adjacent segments.")
                    print("No new connection needs to be made")
                elif i == 0:
                    # First segment (only a segment after)
                    after = headers[i + 1]
                    print(f"Self IP found in {header}. The segment after is: {after}")
                    self.check_adjacent_nano(data[after])
                elif i == len(headers) - 1:
                    # Last segment (only a segment before)
                    before = headers[i - 1]
                    print(f"Self IP found in {header}. The segment before is: {before}")
                    self.check_adjacent_nano(data[before])
                    # print(os.environ['PATH'])

                else:
                    # Middle segment (both before and after)
                    before = headers[i - 1]
                    after = headers[i + 1]
                    print(f"Self IP found in {header}. It is between {before} and {after}")
                break

        if not found:
            print("No new connection to make")

    def check_adjacent_nano(self, adjacent_segment):
        # print(adjacent_segment["ip.number"])
        response = ping(adjacent_segment["ip.number"], count=4, verbose=False)
        if response.success():
            print(f"Success: Device at {adjacent_segment['ip.number']} is reachable.")
        else:
            print(f"Failure: Device at {adjacent_segment['ip.number']} is not reachable.")
