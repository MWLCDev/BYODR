import socket
import logging
import threading
import time
import json
import numpy as np
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"



class Segment_server(threading.Thread):

    # Method that is called after the class is being initiated, to give it its values
    def __init__(self, arg_server_ip, arg_server_port, arg_timeout):
        super(Segment_server, self).__init__()
        
        # Giving the class the values from the class call
        self.server_ip = arg_server_ip
        self.server_port = arg_server_port
        self.timeout = arg_timeout # Maybe 100ms
        self.movement_command_received = ""
        self.reply_to_client = "Im the server"

        # The server socket that will wait for clients to connect
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.server_ip, self.server_port))


    # Method that starts executing when we start an instance of the class as a thread.
    def run(self):

        self.server_socket.listen() # Server starts waiting for clients to connect. Blocking function

        while True:
            try:
                logger.info(f"[Server] Server is listening on {(self.server_ip, self.server_port)}")
                client_socket, client_address = self.server_socket.accept() # Waiting for clients to connect. Blocking function
                logger.info(f"[Server] {client_address} connected.")


                # Starting actions when a client connects. 
                self.communicate_with_client(client_socket)

            except Exception as e:
                logger.error(f"[Server] Got error exception: {e}")


    # Method that first receives and then sends a reply to the client
    def communicate_with_client(self, arg_client_socket):

        counter = 0
        trip_time = np.array([])
        

        while True:
            try:

                # We set the timeout that the server will wait for data from the client
                arg_client_socket.settimeout(self.timeout)

                time_counter = time.perf_counter()
                counter = counter + 1

                # Receiving message from the client
                data_received = arg_client_socket.recv(512).decode("utf-8")

                # Checking if the data received is a JSON string or a normal string
                try:
                    self.movement_command_received = json.loads(data_received) # Its a json
                except (ValueError, TypeError) as e:
                    self.movement_command_received = data_received # Its a normal string

                if counter == 200:
                    logger.info(f"[Server] Received data from client: {self.movement_command_received}")

                # Sending reply to the client
                if counter == 200:
                    logger.info(f"[Server] Sending reply to client: {self.reply_to_client}")
                arg_client_socket.send(self.reply_to_client.encode("utf-8"))

                time_counter_stop = time.perf_counter()

                trip_time = np.append(trip_time, (time_counter_stop-time_counter)*1000)
                if counter == 200:
                    logger.info(f"[Server] Server ended 200 rounds. It took avg {np.sum(trip_time) / trip_time.size:.3f}ms")
                    logger.info(f"[Server] Server ended 200 rounds. It took max {np.max(trip_time):.3f}ms")
                    logger.info(f"[Server] Server ended 200 rounds. It took min {np.min(trip_time):.3f}ms")
                    print("\n\n")

                    trip_time = np.array([])
                    counter = 0

            # Catching potential exceptions and exiting the communication loop
            except socket.timeout:
                logger.error("[Server] 100ms passed without receiving data from the client")
                break
            except ConnectionResetError:
                logger.error("[Server] Client disconnected.")
                break
            except Exception as e:
                logger.error(f"[Server] Got error during communication: {e}")
                break