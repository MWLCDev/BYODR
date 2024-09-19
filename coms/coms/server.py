import socket
import logging
import json


# Declaring the logger
logger = logging.getLogger(__name__)

class SegmentServer:
    """Encapsulate the server functionalities of the segment.

    Args:
        arg_server_ip (Str): IP of the server -> '192.168.1.100'
        arg_server_port (Int): Port that the server uses -> '1111'
        arg_timeout (Float): Server socket timeout -> '0.1' (In seconds)
    """

    # Method that is called after the class is being initiated, to give it its values
    def __init__(self, arg_server_ip, arg_server_port, arg_timeout):
        # Giving the class the values from the class call
        self.server_ip = arg_server_ip
        self.server_port = arg_server_port
        self.timeout = arg_timeout  # Maybe 100ms
        self.msg_to_client = {"rep": "-"}
        self.msg_from_client = {"msg": "-"}
        self.prev_msg = None
        self.processed_command = {"cmd": "-"}

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
                self.client_socket, self.client_address = self.server_socket.accept()  # Waiting for clients to connect. Blocking function
                logger.info(f"[Server] New client {self.client_address} connected.")
                self.client_socket.settimeout(self.timeout)  # We set the timeout that the server will wait for data from the client

                # Starting actions when a client connects.
                # We break from this loop so that the code can move on to different function calls
                break

            except Exception as e:
                logger.error(f"[Server] Got error while waiting for client: {e}")
                logger.exception("[Server] Exception details:")
                pass

    # Sending to the client
    def send_to_LD(self):
        message_to_send = json.dumps(self.msg_to_client).encode("utf-8")
        self.client_socket.send(message_to_send)

    # Receiving from the client
    def recv_from_LD(self):
        recv_message = self.client_socket.recv(512)

        try:
            self.msg_from_client = json.loads(recv_message.decode("utf-8"))
            self.prev_msg = self.msg_from_client
        except json.JSONDecodeError as e:
            logger.error(f"[Server] Error while decoding JSON from client: {e}")
            self.msg_from_client = self.prev_msg
