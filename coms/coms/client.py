import socket
import logging
import time
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"



# Declaring the info of the server
SERVER_PORT = 1111
SERVER_IP = nano_ip # Change to fit the lead's IP
FORMAT = "utf-8"


# Sending data from this segment to a follower segment
# This function will be called after a follower segment connects to the server that starts at line 80
def receive_data(function_client_socket):
    

    while True:
        try:
            time_counter = time.perf_counter()
            # Receiving data from the lead segment
            received_message = function_client_socket.recv(512).decode(FORMAT)
            logger.info(f"Received data from the lead:<<{received_message}>>")

            # Sending reply to the lead segment
            function_client_socket.send(f"This is the follower.".encode(FORMAT))
            time_counter_stop = time.perf_counter()


            logger.info(f"Finished the job. It took {(time_counter_stop-time_counter)*1000}ms")
            time.sleep(2)



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