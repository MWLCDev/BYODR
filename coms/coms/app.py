import logging
import multiprocessing
import threading
import queue
import socket
import copy
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.ssh import Nano
nano_ip = Nano.get_ip_address()
from .server import Segment_server
from .client import Segment_client
from .command_processor import process

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

# A queue that will store messages received by the server of the segment
msg_from_server_queue = queue.Queue(maxsize=1)


# Declaring the inter-service sockets

# Other socket located on pilot/app.py/140
coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

# Other socket located on teleop/app.py/306
teleop_receiver = json_collector(url='ipc:///byodr/teleop_to_coms.sock', topic=b'aav/teleop/input', event=quit_event)

# Other socket located on vehicles/rover/app.py/34
vehicle_receiver = json_collector(url='ipc:///byodr/velocity_to_coms.sock', topic=b'ras/drive/velocity', event=quit_event)

# Creating the segment client and server classes
segment_server = Segment_server(local_ip, nano_port, 0.1) # The server that will wait for the lead to connect
segment_client = Segment_client(follower_ip, nano_port, 0.1) # The client that will connect to a follower


def main():

    # Starting the receivers
    teleop_receiver.start()
    vehicle_receiver.start()

    # Starting the functions that will allow the client and server of each segment to start sending and receiving data
    client_interface_thread = threading.Thread( target=client_code )
    server_interface_thread = threading.Thread( target=server_code )
    client_interface_thread.start()
    server_interface_thread.start()

    # Closing the threads when the executions finish
    client_interface_thread.join()
    server_interface_thread.join()



def client_code():
    counter_client = 0

    while True:

        segment_client.connect_to_server()

        while True:
            counter_client = counter_client + 1

            # Receiving movement commands from Teleop and sending them to Pilot/app
            # This block will be called by the head segment, since only the head receives commands from its own teleop
            if local_ip == "192.168.1.100":
                original_message = teleop_receiver.get()

                # The code will get stuck in this loop, until COM gets non-None type commands from teleop
                while original_message is None:
                    original_message = teleop_receiver.get()

            # This block will be called by a segment that receives commands from its LD
            else:
                # Using get() will make the command wait for a data packet to be availabie in the queue, so that it can be retrieved
                # Using get_nowait() will make the command get whatever is inside, and if its empty, it raises an exception (except queue.Empty)
                try:
                    original_message = msg_from_server_queue.get_nowait()
                
                except queue.Empty:
                    # If the queue is empty, we will wait for the queue to be full
                    original_message = msg_from_server_queue.get()

            # Making a new seperate object that has the same values as the original message
            # Using message_to_send = original_message_to_send, creates a reference(message_to_send) to the same object in memory(original_message_to_send)
            # We need this because if we use "message_to_send = original_message_to_send", or just use original_message_to_send everywhere
            # changes in the value of message_to_send will be reflected on the value of original_message_to_send, thus altering the values that we get from the teleop_receiver 
            message_to_send = copy.deepcopy(original_message)
            # Try testing this:
            # import copy

            # original_dict = {"ValA": 1, "ValB": 2}

            # # Simple assignment (creates a reference)
            # copied_dict_ref = original_dict

            # # Deep copy (creates a new object)
            # copied_dict_deepcopy = copy.deepcopy(original_dict)

            # # Modifying the original dictionary
            # copied_dict_ref["ValA"] = 1000

            # print("Original Dict:", original_dict)
            # print("Copied Dict (Reference):", copied_dict_ref)
            # print("Copied Dict (Deepcopy):", copied_dict_deepcopy)

            # Running the above snippet gives these results:
            # Original Dict: {'ValA': 1000, 'ValB': 2}
            # Copied Dict (Reference): {'ValA': 1000, 'ValB': 2}
            # Copied Dict (Deepcopy): {'ValA': 1, 'ValB': 2}



            try:

                ######################################################################################################
                # Main part of the send/recv of the client
                    
                # Processing the command before sending it to the FL
                process(message_to_send)

                # Sending the command to our FL
                segment_client.send_to_FL(message_to_send)

                # Sending commands to our local pilot service
                coms_to_pilot_publisher.publish(message_to_send)

                # Receiving a reply from the FL
                reply_from_server = segment_client.recv_from_FL()

                if counter_client == 200:
                    logger.info(f"[Client] Got reply from server: {reply_from_server}")
                    counter_client = 0
            

                ######################################################################################################

            # Catching potential exceptions and attempting to reconnect each time
            except ConnectionResetError:
                logger.error("[Client] Server disconnected")
                break
                
            except socket.timeout:
                logger.error("[Client] 100ms passed without receiving data from the server")
                break

            except Exception as e:
                logger.error(f"[Client] Got error during communication: {e}")
                break


def server_code():
    counter_server = 0

    while True:

        segment_server.start_server()

        while True:
            counter_server = counter_server + 1

            try:

                ######################################################################################################
                # Main part of the send/recv of the server

                # Receiving movement commands from the LD
                message_from_client = segment_server.recv_from_LD()

                # Placing the message from the server in the queue
                # Using put() will make the command wait for a free spot on the queue.
                # Using put_nowait() will make the command add the data in the queue and raise an exception if its already full (except queue.Full)
                try:
                    msg_from_server_queue.put_nowait(message_from_client)
                
                except queue.Full:
                    # If the queue is full, we empty it, and try to place the data again, but this time we will wait for the queue to be empty
                    msg_from_server_queue.get()
                    msg_from_server_queue.put(message_from_client)

                if counter_server == 200:
                    logger.info(f"[Server] Got message from client: {message_from_client}")
                    counter_server = 0

                # Sending a reply to the LD
                segment_server.send_to_LD({"Message": "I got your message"})

            ######################################################################################################

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


if __name__ == "__main__":
    main()