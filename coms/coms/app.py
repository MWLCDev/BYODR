import logging
import multiprocessing
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()
from .server import Segment_server
from .client import Segment_client

quit_event = multiprocessing.Event()


# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Getting the IP of the local machine
local_ip = Nano.get_ip_address()
nano_port = 1111

# Getting the follower/lead IPs from the local IP. (Temporary, until we get the robot config file)
follower_ip = "192.168." + str( int(local_ip[8])+1 ) + ".100"
lead_ip = "192.168." + str( int(local_ip[8])-1 ) + ".100"



# Declaring the inter-service sockets

# Other socket located on pilot/app.py/140
coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

# Other socket located on teleop/app.py/306
teleop_receiver = json_collector(url='ipc:///byodr/teleop_to_coms.sock', topic=b'aav/teleop/input', event=quit_event)

# Other socket located on vehicles/rover/app.py/34
vehicle_receiver = json_collector(url='ipc:///byodr/velocity_to_coms.sock', topic=b'ras/drive/velocity', event=quit_event)

def main():
    
    # Creating the segment client and server classes
    segment_server = Segment_server(local_ip, nano_port, 0.1) # The server that will wait for the lead to connect
    segment_client = Segment_client(follower_ip, nano_port, 0.1) # The client that will connect to a follower

    # Starting the receivers
    teleop_receiver.start()
    vehicle_receiver.start()

    # Starting the server and client
    segment_server.start()
    segment_client.start()

    while True:

        # Receiving velocity of the motors from Vehicles
        # logger.info(f"Velocity received: {vehicle_receiver.get()}.")

        # Receiving movement commands from Teleop and sending them to Pilot/app
        movement_commands_from_teleop = teleop_receiver.get()
        
        # logger.info(f"Sending to pilot: {repr(movement_commands_from_teleop)}.")
        if movement_commands_from_teleop != None:
            coms_to_pilot_publisher.publish(movement_commands_from_teleop)
            segment_client.msg_to_send = str(movement_commands_from_teleop)





if __name__ == "__main__":
    main()