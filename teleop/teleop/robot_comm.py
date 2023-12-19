import zmq
import json
import threading, time
from byodr.utils.ssh import Router, Nano
import logging
import configparser


logger = logging.getLogger(__name__)


# This file will have the ZMQ socket and dealing with the robot configuration file


class DataSubscriberThread(threading.Thread):
    def __init__(self, ip, event, sub_port=5454, req_port=5455):
        # Set up necessary attributes and methods that DataSubscriberThread inherits from Thread.
        # Use the thread control methods like start(), join(), is_alive().
        super(DataSubscriberThread, self).__init__()
        self._ip = ip
        self._sub_port = sub_port
        self._req_port = req_port
        self._quit_event = event

        self.context = zmq.Context()
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self._ip}:{self._req_port}")

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{self._ip}:{self._sub_port}")
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
                    print(f"Received: {message}")
                    # Process message here
        finally:
            self.req_socket.send_string(f"DISCONNECT {subscriber_ip}")
            logging.info("DataSubscriberThread is about to close")

            self.req_socket.recv()
            self.cleanup()

    def cleanup(self):
        self.sub_socket.close()
        self.req_socket.close()
        self.context.term()


def process_message(message):
    if "change segment order" in message:
        print("1")
    elif "delete segment" in message:
        print("2")
    else:
        print("Unknown command.")


class DataPublisher:
    def __init__(self, robot_config_dir, message=" ", sleep_time=5, pub_port=5454, rep_port=5455):
        self.ip = Nano.get_ip_address()
        self.pub_port = pub_port
        self.rep_port = rep_port
        self.robot_config_dir = robot_config_dir
        self.message = message
        self.sleep_time = sleep_time
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://{self.ip}:{self.pub_port}")
        # Reply socket to get announcement message when a subscriber connects or disconnects
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://{self.ip}:{self.rep_port}")
        self.subscriber_ips = set()

    def start_publishing(self):
        try:
            while True:
                self.check_subscribers()
                # Read .ini file
                config = configparser.ConfigParser()
                config.read(self.robot_config_dir)
                ini_data = {section: dict(config.items(section)) for section in config.sections()}

                # Convert to JSON
                json_data = json.dumps(ini_data)

                # Send JSON data to subscribers
                combined_message = f"{self.message} {json_data}"
                print(f"Sent {combined_message}")
                self.pub_socket.send_string(combined_message)
                time.sleep(self.sleep_time)

        except KeyboardInterrupt:
            print("Interrupted, closing sockets and terminating context...")
        finally:
            self.pub_socket.close()
            self.rep_socket.close()
            self.context.term()

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
