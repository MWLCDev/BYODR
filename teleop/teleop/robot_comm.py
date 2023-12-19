import zmq
import json
import threading, time
from byodr.utils.ssh import Router, Nano
import logging
import configparser


logger = logging.getLogger(__name__)


# This file will have the ZMQ socket and dealing with the robot configuration file


def subscribe_data(ip="192.168.1.100", sub_port=5454, req_port=5455):
    context = zmq.Context()
    subscriber_ip = Nano.get_ip_address()
    # REQ socket for sending connection and disconnection messages
    req_socket = context.socket(zmq.REQ)
    req_socket.connect(f"tcp://{ip}:{req_port}")

    # Notify the publisher of the connection
    req_socket.send_string(f"CONNECT {subscriber_ip}")
    req_socket.recv()  # Wait for acknowledgement

    # SUB socket for receiving data
    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect(f"tcp://{ip}:{sub_port}")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    # Poller for non-blocking wait
    poller = zmq.Poller()
    poller.register(sub_socket, zmq.POLLIN)

    try:
        while True:
            # Non-blocking wait for a message
            socks = dict(poller.poll(0))  # Timeout is 0 for non-blocking
            if sub_socket in socks and socks[sub_socket] == zmq.POLLIN:
                message = sub_socket.recv_string()
                print(f"Received: {message}")
                # Your message processing logic here
    except KeyboardInterrupt:
        print("Interrupted, closing socket.")
    finally:
        # Notify the publisher of the disconnection
        req_socket.send_string(f"DISCONNECT {subscriber_ip}")
        req_socket.recv()

        sub_socket.close()
        req_socket.close()
        context.term()


def process_message(message):
    if "change segment order" in message:
        print("1")
    elif "delete segment" in message:
        print("2")
    else:
        print("Unknown command.")


class DataPublisher:
    def __init__(self, robot_config_dir, message, sleep_time=5, pub_port=5454, rep_port=5455):
        self.ip = Nano.get_ip_address()
        self.pub_port = pub_port
        self.rep_port = rep_port
        self.robot_config_dir = robot_config_dir
        self.message = message
        self.sleep_time = sleep_time
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://{self.ip}:{self.pub_port}")
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://{self.ip}:{self.rep_port}")
        self.subscriber_ips = set()

    def start_publishing(self):
        try:
            while True:
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
