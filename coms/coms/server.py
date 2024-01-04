import socket
import logging
import time
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"



# Variables for the server to start
PORT = 1111
IP = nano_ip
FORMAT = "utf-8"



# Sending data from this segment to a follower segment
# This function will be called after a follower segment connects to the server that starts at line 80
def send_data(function_client_socket, function_client_address):
    

    logger.info(f"[NEW CONNECTION] {function_client_address} connected.")
    

    while True:
        try:
            time_counter = time.perf_counter()

            # Sending test string to the follower segment
            function_client_socket.send(f"This is the lead with address {IP}:{PORT}".encode(FORMAT))

            # Receiving reply from the follower segment
            received_message = function_client_socket.recv(512).decode(FORMAT)
            time_counter_stop = time.perf_counter()

            logger.info(f"Received reply from follower. It took {(time_counter_stop-time_counter)*1000}ms")

            time.sleep(2)

        except ConnectionResetError:
            logger.info("Client disconnected.")
        except Exception as e:
            logger.info(f"Got error trying to send to client: {e}")



# Start listening for connections and passing to handler
def start_server():

    # Binding the IP and port to our socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP, PORT))

    # Start accepting potential clients
    server.listen()

    # server.settimeout(1) # We set the timeout to 1 second.
    logger.info(f"Server is listening on {(IP, PORT)}")

    # Blocks execution until a client connects.
    client_socket, client_address = server.accept()

    send_data(client_socket, client_address)            
