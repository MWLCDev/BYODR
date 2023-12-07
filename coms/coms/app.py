import logging
import threading
import multiprocessing
from byodr.utils.ip_getter import get_ip_number
from byodr.utils.ipc import JSONZmqClient, JSONServerThread, ReceiverThread
from .server import start_server
from .client import connect_to_server

quit_event = multiprocessing.Event()


# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Getting the third octet of the IP of the local machine
local_third_ip_digit = get_ip_number()


def _on_receive(message):
    logger.info(f"Data received from the Pilot-relay service, Listener: {message}.")

def _on_message(message):
    # logger.info(f"Data received from the Teleop service, Listener: {message}.")
    pass


# Declaring the inter-service sockets
pilot_publisher = JSONZmqClient(urls="ipc:///byodr/coms_to_pilot.sock")

teleop_receiver = JSONServerThread(url="ipc:///byodr/teleop_to_coms.sock", event=quit_event, receive_timeout_ms=50)
teleop_receiver.message_to_send = "Coms"
teleop_receiver.add_listener(_on_message)

velocity_receiver = ReceiverThread(url='ipc:///byodr/velocity_to_coms.sock', topic=b'ras/drive/velocity')
velocity_receiver.add_listener(_on_receive)

def main():

    # Getting the 3rd digit of the IP of the local device
    local_third_ip_digit = get_ip_number()

    # Starting the receivers
    teleop_receiver.start()
    velocity_receiver.start()

    while True:
        # Setting test data to the inter-service sockets
        reply_from_pilot = pilot_publisher.call(dict(data = "Coms"))
        # logger.info(f"Message received from Pilot: {reply_from_pilot}")


    # Threads that will be executing the server and client codes
    server_thread = threading.Thread( target = start_server )
    client_thread = threading.Thread( target = connect_to_server )


    # Each segment, regardless of IP, will be a server, so that their follower can connect to them.
    logger.info(f"Starting the server code...")
    server_thread.start()

    # All other IPs will be clients except the first segment of the robot,
    # since there is no "0th" segment
    if local_third_ip_digit != '1':
        logger.info(f"Starting the client code...")
        client_thread.start()

    # When the threads finish executing they exit
    #################### We might not need this part###############################
    server_thread.join()
    client_thread.join()


if __name__ == "__main__":
    main()