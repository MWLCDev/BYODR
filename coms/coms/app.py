import logging
import threading
import multiprocessing
import time
from byodr.utils.ip_getter import get_ip_number
from byodr.utils.ipc import JSONPublisher, json_collector
from .server import start_server
from .client import connect_to_server

quit_event = multiprocessing.Event()


# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Getting the third octate of the IP of the local machine
local_third_ip_digit = get_ip_number()


# Declaring the inter-service sockets

# Other socket located on pilot/app.py/140
coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

# Other socket located on teleop/app.py/306
teleop_receiver = json_collector(url='ipc:///byodr/teleop_to_coms.sock', topic=b'aav/teleop/input', event=quit_event)

# Other socket located on vehicles/rover/app.py/34
vehicle_receiver = json_collector(url='ipc:///byodr/velocity_to_coms.sock', topic=b'ras/drive/velocity', event=quit_event)

def main():
    
    # Getting the 3rd digit of the IP of the local device
    local_third_ip_digit = get_ip_number()

    # Starting the receivers
    teleop_receiver.start()
    vehicle_receiver.start()

    while True:
        # Receiving movement commands from Teleop and sending them to Pilot/app
        movement_commands_from_teleop = teleop_receiver.get()

        # We do not send commands to pilot, if the throttle is 0
        if not movement_commands_from_teleop == None:
            if not movement_commands_from_teleop.get('throttle') == 0:
                # logger.info(f"Sending to pilot: {movement_commands_from_teleop}.")
                coms_to_pilot_publisher.publish(movement_commands_from_teleop)



        # Receiving velocity of the motors from Vehicles
        # logger.info(f"Velocity received: {vehicle_receiver.get()}.")

        time.sleep(1./1000)

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