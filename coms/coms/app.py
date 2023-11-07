import logging
import threading
import multiprocessing
from byodr.utils.ip_getter import get_ip_number
from byodr.utils.ssh_to_router import get_router_arp_table, get_filtered_router_arp_table
from byodr.utils.ipc import json_collector, JSONPublisher, ReceiverThread
from .server import start_server
from .client import connect_to_server

quit_event = multiprocessing.Event()


# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Getting the third octet of the IP of the local machine
local_third_ip_digit = get_ip_number()


# # Declaring the inter-service sockets
# pilot_publisher = JSONPublisher(url="ipc:///byodr/com.sock", topic="aav/com/commands")
# teleop_receiver = json_collector(url="ipc:///byodr/teleop.sock",
#         topic=b"aav/teleop/input",
#         event=quit_event,
#         hwm=20)
# servos_receiver = ReceiverThread('tcp://192.168.' + local_third_ip_digit + '.32:5555',
#                                  topic=b'ras/drive/status')

# # Those socket classes that stephan made, inherit from threading.Thread, so we have to .start()
# pilot_publisher.start()
# teleop_receiver.start()
# servos_receiver.start()


# Function that will run every time we receive a message from the Servos of Pi
def servos_listener_function(msg):
    msg.get()



def main():

    # # Adding a listener function to the servos listener socket
    # servos_receiver.add_listener(servos_listener_function)


    # Getting the 3rd digit of the IP of the local device
    local_third_ip_digit = get_ip_number()


    arp_list = get_router_arp_table()  
    filtered_list = get_filtered_router_arp_table(arp_list, local_third_ip_digit)


    # To be able too see a nice table on logger
    log_string = "IP address".ljust(20) + "Flags\n"
    for entry in filtered_list:
        log_string += entry['IP address'].ljust(20) + entry['Flags'] + "\n"
    logger.info(f"Output filtered list:\n{log_string}from 192.168.{local_third_ip_digit}.1")


    # # Setting test data to the inter-service sockets
    # pilot_publisher.publish("This is coms")
    # logger.info(f"Message received from Teleop: {teleop_receiver.get()}")
    # logger.info(f"Message received from Servos: {servos_receiver.pop_latest()}")


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