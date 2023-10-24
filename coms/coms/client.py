import socket
import logging
import time
from byodr.utils.ip_getter import get_ip_number



# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"


# Getting the 3rd digit of the IP of the local device
local_third_ip_digit = get_ip_number()

# Setting the lead's IP, assuming that it will always be -1 less than the local one
lead_third_ip_digit = str ( int(local_third_ip_digit) - 1 )


# Declaring the info of the server
SERVER_PORT = 1111
SERVER_IP = "192.168."+ lead_third_ip_digit +".100"
FORMAT = "utf-8"


# Sending data from this segment to a follower segment
# This function will be called after a follower segment connects to the server that starts at line 80
def receive_data(function_client_socket):
    
    previous_time_counter = 0
    time_counter = time.perf_counter()

    while True:
        try:
            # Receiving data from the lead segment
            received_message = function_client_socket.recv(512).decode(FORMAT)
            logger.info(f"Received data from the lead:<<{received_message}>>")

            # Sending reply to the lead segment
            function_client_socket.send(f"This is the follower.".encode(FORMAT))

            logger.info(f"Finished the job. It took {time_counter-previous_time_counter}ms")
            previous_time_counter = time_counter


        except Exception as e:
            logger.info(f"Got error while sending: {e}")


def connect_to_server():
    
    # Declaring the local socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.info(f"Trying to connect to the server...")

    while True:
        # Connecting to the server
        try:
            client.connect((SERVER_IP, SERVER_PORT))
            logger.info(f"[NEW CONNECTION] Conencted to server.")

        # Error handling
        except ConnectionRefusedError:
            logger.info("Connection was refused. Server may not be running.")
        except TimeoutError:
            logger.info("Connection attempt timed out. Server may not be responding.")
        except OSError as e:
            logger.info(f"Socket error: {e}")
        except Exception as e:
            logger.info(f"Got error while connecting: {e}")
        else:
            receive_data(client)