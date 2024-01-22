import socket
import logging
import time
import json
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"




class Segment_client():
    """Class that encapsulates the client functionalities of the segment.
        Methods:
            - connect_to_server(): Tries to connect to the server
            - close_connection(): Closes the connection to the server
            - start_server(): The server starts listening for clients
            - send_to_FL(): The client sends data to its FL
            - recv_from_FL(): The client receives a reply from its FL

        Args:
            arg_server_ip (Str): IP of the server -> '192.168.1.100'
            arg_server_port (Int): Port that the server uses -> '1111'
            arg_timeout (Float): Client socket timeout -> '0.1' (In seconds)
        """

    # Method that is called after the class is being initiated, to give it its values
    def __init__(self, arg_server_ip, arg_server_port, arg_timeout):
        # Giving the class the values from the class call
        self.server_ip = arg_server_ip # The IP of the server that the client will connect to
        self.server_port = arg_server_port # The port of the server that the client will connect to
        self.timeout = arg_timeout # Maybe 100ms
        self.socket_initialized = False # Variable that keeps track if we have a functioning socket to a server
        self.msg_to_server = None
        self.msg_from_server = None

        # The client socket that will connect to the server
        self.client_socket = None


    # Establish the connection to the server
    def connect_to_server(self):
            
        try:
            # Close the current socket, if it exists
            self.close_connection()

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Remake the socket and reconnect
            self.client_socket.settimeout(self.timeout) # Set the timeout for all the back and forth between the server/client
            self.client_socket.connect((self.server_ip, self.server_port)) # Connect to the server
            logger.info("[Client] Connected to server.")
            self.socket_initialized = True

        except Exception as e:
            # logger.warning(f"[Client] Got error trying to connect to the server: {e}.\nTrying to reconnect...")
            # logger.exception("[Client] Exception details:")
            time.sleep(2)  # Wait for a while before retrying


    # Close the malfunctioning socket if we lose connection to the server.
    # We will make a new one and try to reconnect
    def close_connection(self):
        
        while self.socket_initialized:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
                self.socket_initialized = False
            except Exception as e:
                # logger.warning(f"[Client] Error while closing socket: {e}")
                # logger.exception("[Client] Exception details:")
                time.sleep(2)


    # Sending data to the server
    def send_to_FL(self):
        message_to_send = json.dumps(self.msg_to_server)
        self.client_socket.send(message_to_send.encode("utf-8"))


    # Receiving data from the server
    def recv_from_FL(self):
        self.msg_from_server = self.client_socket.recv(512).decode("utf-8")