import socket
import logging
import time
import json
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"



class Segment_server():

    # Method that is called after the class is being initiated, to give it its values
    def __init__(self, arg_server_ip, arg_server_port, arg_timeout):
        
        # Giving the class the values from the class call
        self.server_ip = arg_server_ip
        self.server_port = arg_server_port
        self.timeout = arg_timeout # Maybe 100ms

        # The server socket that will wait for clients to connect
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.server_ip, self.server_port))
        self.server_socket.listen()

        # Variables that will store the data of the client socket when/if the client connects
        self.client_socket = None
        self.client_address = None
    

    # Starting the server
    def start_server(self):
        
        while True:
            try:
                logger.info(f"[Server] Server is listening on {(self.server_ip, self.server_port)}")
                self.client_socket, self.client_address = self.server_socket.accept() # Waiting for clients to connect. Blocking function
                logger.info(f"[Server] {self.client_address} connected.")
                self.client_socket.settimeout(self.timeout) # We set the timeout that the server will wait for data from the client


                # Starting actions when a client connects.
                # We break from this loop so that the code can move on to different function calls
                break

            except Exception as e:
                logger.error(f"[Server] Got error while waiting for client: {e}")

# Check for None messages being passed around
# And check if i can not execute an if every time i want to send a message

    # Sending to the client
    def send_to_LD(self, message_to_send):
        
        if message_to_send is None:
            message_to_send = "I am the server"

        self.client_socket.send(message_to_send.encode("utf-8"))



    # Receiving from the client
    def recv_from_LD(self):
        
        # Receiving message from the client
        recv_message = self.client_socket.recv(512).decode("utf-8")

        # Checking if the data received is a JSON string or a normal string
        try:
            decoded_message = json.loads(recv_message) # Its a json
        except (ValueError, TypeError) as e:
            decoded_message = recv_message # Its a normal string
        
        return decoded_message
