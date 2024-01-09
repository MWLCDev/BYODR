import socket
import logging
import time
import threading
import json
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"




class Segment_client(threading.Thread):

    # Method that is called after the class is being initiated, to give it its values
    def __init__(self, arg_server_ip, arg_server_port, arg_timeout):
        super(Segment_client, self).__init__()
        
        # Giving the class the values from the class call
        self.server_ip = arg_server_ip # The IP of the server that the client will connect to
        self.server_port = arg_server_port # The port of the server that the client will connect to
        self.timeout = arg_timeout # Maybe 100ms
        self.reply_from_server = "" 
        self.msg_to_send = "I am the client"
        self.socket_initialized = False # Variable that keeps track if we have a socket to a server running

        # The client socket that will connect to the server
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    # Establish the connection to the server
    def connect_to_server(self):
            
            # Try to reconnect to the server until we connect
            while True:
                try:
                    # Close the current socket, if it exists
                    self.close_connection()

                    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Remake the socket and reconnect
                    self.client_socket.settimeout(self.timeout) # Set the timeout for all the back and forth between the server/client
                    self.client_socket.connect((self.server_ip, self.server_port)) # Connect to the server
                    logger.info("[Client] Connected to server.")
                    self.socket_initialized = True
                    break

                except Exception as e:
                    logger.warning(f"[Client] Got error trying to connect to the server: {e}.\nTrying to reconnect...")
                    time.sleep(2)  # Wait for a while before retrying


    # Close the malfunctioning socket if we lose connection to the server.
    # We will make a new one and try to reconnect
    def close_connection(self):
        
        if self.socket_initialized:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
                self.socket_initialized = False
            except Exception as e:
                logger.warning(f"[Client] Error while closing socket: {e}")


    # Communicating with the server        
    def run(self):
        
        # Connecting to the server
        self.connect_to_server()

        counter = 0
        time_stop = 0


        while True:
            try:
                time_counter = time.perf_counter()
                counter = counter + 1

                # Sending test data to the server. If its a dictionary (movement commands), we encode it to json first
                # if time_counter - time_stop >= 1:
                #     logger.info(f"[Client] Sending data to server: {self.msg_to_send}")
                
                # Checking to see if we are sending a dictionary (movement commands) or a normal string
                if type(self.msg_to_send) is dict: # We try to send a dictionary (movement commands)
                    json_formatted_commands = json.dumps(self.msg_to_send)
                    self.client_socket.send(json_formatted_commands.encode("utf-8"))
                else:
                    self.client_socket.send(self.msg_to_send.encode("utf-8")) # We try to send a normal string
                
                # Receiving data from the server
                self.reply_from_server = self.client_socket.recv(512).decode("utf-8")
                # if time_counter - time_stop >= 1:
                #     logger.info(f"[Client] Received reply from the server: {self.reply_from_server}")
                
                if time_counter - time_stop >= 1:
                    time_stop = time_counter
                    logger.info(f"[Client] In 1 second sent/received {counter} commands")
                    counter = 0


            # Catching potential exceptions and attempting to reconnect each time
            except ConnectionResetError:
                logger.error("[Client] Server disconnected")
                self.connect_to_server()
            except socket.timeout:
                logger.error("[Client] 100ms passed without receiving data from the server")
                self.connect_to_server()
            except Exception as e:
                logger.error(f"[Client] Got error during communication: {e}")
                self.connect_to_server()