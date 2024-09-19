import socket
import logging
import time
import json


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"


class Segment_client:
    """Encapsulate the client functionalities of the segment.

    Args:
        arg_server_ip (Str): IP of the server -> '192.168.1.100'
        arg_server_port (Int): Port that the server uses -> '1111'
        arg_timeout (Float): Client socket timeout -> '0.1' (In seconds)
    """

    # Method that is called after the class is being initiated, to give it its values
    def __init__(self, arg_server_ip, arg_server_port, arg_timeout):
        # Giving the class the values from the class call
        self.server_ip = arg_server_ip  # The IP of the server that the client will connect to
        self.server_port = arg_server_port  # The port of the server that the client will connect to
        self.timeout = arg_timeout  # Maybe 100ms
        self.socket_initialized = False  # Variable that keeps track if we have a functioning socket to a server
        self.msg_to_server = {"cmd": "-"}
        self.msg_from_server = {"rep": "-"}
        self.prev_msg = None
        self.client_socket = None  # The client socket that will connect to the server

    # Establish the connection to the server
    def connect_to_server(self):
        # Close the current socket, if it exists
        if self.client_socket is not None:
            self.close_connection()

        while not self.socket_initialized:
            try:
                # logger.info(f"[Client] Trying to connect the server: {self.server_ip}:{self.server_port}...")
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Remake the socket and reconnect
                self.client_socket.settimeout(self.timeout)  # Set the timeout for all the back and forth between the server/client
                self.client_socket.connect((self.server_ip, self.server_port))  # Connect to the server
                logger.info(f"[Client] Connected to server {(self.server_ip, self.server_port)}.")
                self.socket_initialized = True

            except Exception as e:
                # logger.warning(f"[Client] Got error trying to connect to the server: {e}.\nTrying to reconnect...")
                # logger.exception("[Client] Exception details:")
                time.sleep(2)  # Wait for a while before retrying

    # Close the malfunctioning socket if we lose connection to the server.
    # We will make a new one and try to reconnect
    def close_connection(self):
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
            self.socket_initialized = False
        except Exception as e:
            logger.warning(f"[Client] Error while closing socket: {e}")
            logger.exception("[Client] Exception details:")
            time.sleep(2)
        finally:
            self.socket_initialized = False

    def send_to_FL(self):
        """Sending data to the server"""
        if self.msg_to_server is not None:
            message_to_send = json.dumps(self.msg_to_server).encode("utf-8")
        else:
            message_to_send = json.dumps({"cmd": "-"}).encode("utf-8")
            logger.warning(f"[Client] Empty message was about to be sent to the server")
        self.client_socket.send(message_to_send)

    def recv_from_FL(self):
        """Receiving data from the server"""
        recv_message = self.client_socket.recv(512).decode("utf-8")

        try:
            self.msg_from_server = json.loads(recv_message)
            self.prev_msg = self.msg_from_server
        except json.JSONDecodeError as e:
            logger.error(f"[Client] Error while decoding JSON from client: {e}")
            self.msg_from_server = self.prev_msg
