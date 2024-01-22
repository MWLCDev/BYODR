import logging
import threading
from collections import deque
import socket
import copy
import time
import multiprocessing
import signal
from byodr.utils.ssh import Nano
from .server import Segment_server
from .client import Segment_client
from .command_processor import process
from .common_utils import IntersegmentCommunication

# This flag starts as false
quit_event = multiprocessing.Event()
quit_event.clear()

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())


# Set the flag as true when we receive interrupt signals
def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()

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

# A deque that will store messages received by the server of the segment
msg_from_server_queue = deque(maxlen=1)

segment_server = Segment_server(local_ip, nano_port, 0.1) # The server that will wait for the lead to connect
segment_client = Segment_client(follower_ip, nano_port, 0.1) # The client that will connect to a follower
socket_interface = IntersegmentCommunication(quit_event) # Class that includes sockets to other services necesassary for segment communication



def communication_between_segments():
    """Use: 
        The main function that starts all other communicaiton functionalities.
        Starts 3 threads:\n
        1- A thread that will receive commands from TEL or LD-COM, depending on the IP of the device calling the function.\n
        2- A thread that starts the functionalities of the client of the segment.\n
        3- A thread that starts the functionalities of the server of the segment.\n

    Returns:
        0 if all threads started close gracefully.
    """


    # Starting the functions that will allow the client and server of each segment to start sending and receiving data
    command_receiver_thread = threading.Thread( target=command_receiver )
    client_interface_thread = threading.Thread( target=client_code )
    server_interface_thread = threading.Thread( target=server_code )

    # Starting the threads of Coms
    socket_interface.start_threads()
    command_receiver_thread.start()
    client_interface_thread.start()
    server_interface_thread.start()

    # Closing the threads when the executions finish
    command_receiver_thread.join()
    client_interface_thread.join()
    server_interface_thread.join()
    socket_interface.join_threads()
    logger.info("Stopped threads in communication.py.")
    return 0


def command_receiver():
    """Use:
        With this function, Coms receives commands from teleop or LD-COMS, and also forwards commands to Pilot.
        In between receiving commands and sending to pilot, the client_interface_thread and server_interface_thread
        edit the value of the command that is about to be sent to pilot

        -If the Head segment calls this function, it will receive commands from its local TEL and then forward them to PIL.\n
        -If any other segment calls this function, it will receive commands from the deque. 
        This deque is being filled up by the server thread, with commands received from its LD segment,

    Returns:
        Nothing
    """
   
    global msg_from_server_queue

    while not quit_event.is_set():

        # The head segment forwards commands from teleop
        # This block is only used by the Head segment
        if local_ip == "192.168.1.100":
            while not quit_event.is_set():

                # Receiving the commands that we will process/forward to our FL, from Teleop
                # The code will get stuck in this loop, until COM gets non-None type commands from teleop
                segment_client.msg_to_server = socket_interface.get_movement_command()
                while segment_client.msg_to_server is None:
                    segment_client.msg_to_server = socket_interface.get_movement_command()


                # Forwarding commands to pilot
                socket_interface.publish_to_pilot(segment_client.msg_to_server)



        # All other segments are forwarding commands from the COM server
        else:
            while not quit_event.is_set():

                # Receiving the commands that we will process/forward to our FL, from our current LD
                try:
                    segment_client.msg_to_server = msg_from_server_queue.pop()
                
                except IndexError:
                    # If the queue is empty, we do nothing and check again later
                    pass


                # Forwarding commands to pilot
                socket_interface.publish_to_pilot(segment_client.msg_to_server)


def client_code():
    """Use:
        The main functionality of the client of the segment. It will try to connect to its assigned server. If it connects successfully,
        will send and then receive (in that order) data from its assigned server.
        If it loses connection with the server, will automatically try to reconnect every 2 seconds

    Returns:
        Nothing
    """

    counter_client = 0
    # time_stop = 0

    
    while not quit_event.is_set():

        # The client will not start unless the command we have from Teleop or our LD is not None
        if segment_client.msg_to_server is not None:
            segment_client.connect_to_server()

        # Start the send/recv cycle only if the socket was successfully made
        while segment_client.socket_initialized and segment_client.msg_to_server is not None:
            time_counter = time.perf_counter()
            counter_client = counter_client + 1

            try:
                ######################################################################################################
                # Main part of the send/recv of the client

                dict_with_velocity = socket_interface.get_velocity()
                if dict_with_velocity is None:
                    logger.warning("[Client] 0 velocity")
                    dict_with_velocity = {'velocity': 0.0}
                
                segment_client.msg_to_server.update(dict_with_velocity)

                # Sending the command to our FL
                segment_client.send_to_FL()

                # Receiving a reply from the FL
                segment_client.recv_from_FL()

                # if time_counter - time_stop >= 1:
                #     # logger.info(f"[Client] Got reply from server: {segment_client.msg_from_server}")
                #     logger.info(f"[Client] Sent message to server: {segment_client.msg_to_server}")
                if counter_client == 50:
                    logger.info(f"[Client] Sent message to server: {segment_client.msg_to_server}")

                    
            
                ######################################################################################################
                stop_time = time.perf_counter()
                # if time_counter - time_stop >= 1:
                #     print(f"[Client] {counter_client} rounds in 1 second")
                #     counter_client = 0
                #     time_stop = time_counter

                if counter_client == 50:
                    logger.info(f"[Client] Got reply from server: {segment_client.msg_from_server}")
                    logger.info(f"[Client] A round took {(stop_time-time_counter)*1000:.3f}ms\n")
                    counter_client = 0

            # Catching potential exceptions and attempting to reconnect each time
            except ConnectionResetError:
                logger.error("[Client] Server disconnected")
                break
                
            except socket.timeout:
                logger.error("[Client] 100ms passed without receiving data from the server")
                break

            except Exception as e:
                logger.error(f"[Client] Got error during communication: {e}")
                logger.exception("[Server] Exception details:")
                break


def server_code():
    """Use:
        The main functionality of the server of the segment. It will setup a socket server and will wait for a client to connect.
        Once a client connects, the server will wait for data, and when it is received, will send back a reply.
        The data received will be appended to a deque. The command receiver thread consumes items from the deque by forwarding commands to the local pilot.

    Returns:
        Nothing
    """

    global msg_from_server_queue
    counter_server = 0
    # time_stop = 0

    while not quit_event.is_set():

        segment_server.start_server()

        while not quit_event.is_set():
            counter_server = counter_server + 1
            time_counter = time.perf_counter()

            try:

                ######################################################################################################
                # Main part of the send/recv of the server

                # Receiving movement commands from the LD
                segment_server.recv_from_LD()
                # if counter_server == 50:
                #     logger.info(f"[Server] Received from client: {segment_server.msg_from_client}")

                # if time_counter - time_stop >= 1:
                #     logger.info(f"[Server] Edited message from client: {segment_server.processed_command}")
                

                # Making a new seperate object that has the same values as the original message
                # Using processed_command = msg_from_client, creates a reference(processed_command) to the same object in memory(msg_from_client)
                # We need deepcopy because if we use "processed_command = msg_from_client", or just use msg_from_client everywhere
                # changes in the value of processed_command will be reflected on the value of msg_from_client, thus altering the values that we get from the teleop_receiver 
                command_to_process = copy.deepcopy(segment_server.msg_from_client)
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

                # Processing the command before sending it to the FL
                if type(command_to_process) is dict:
                    segment_server.processed_command = process(command_to_process)

                    # Placing the message from the server in the queue
                    msg_from_server_queue.append(segment_server.processed_command)


                if counter_server == 50:
                    logger.info(f"[Server] Edited message from client: {segment_server.processed_command}")


                # Sending a reply to the LD
                segment_server.msg_to_client = {"Message": "I got your message"}
                segment_server.send_to_LD()

            ######################################################################################################
                
                stop_time = time.perf_counter()
                # if time_counter - time_stop >= 1:
                #     print(f"[Server] {counter_server} rounds in 1 second")
                #     counter_server = 0
                #     time_stop = time_counter

                if counter_server == 50:
                    logger.info(f"[Server] Sent reply to client: {segment_server.msg_to_client}")
                    logger.info(f"[Server] A round took {(stop_time-time_counter)*1000:.3f}ms\n")
                    counter_server = 0

            # Catching potential exceptions and exiting the communication loop
            except socket.timeout:
                logger.error("[Server] 100ms passed without receiving data from the client")
                break

            except ConnectionResetError:
                logger.error("[Server] Client disconnected.")
                break

            except Exception as e:
                logger.error(f"[Server] Got error during communication: {e}")
                logger.exception("[Server] Exception details:")
                break


if __name__ == "__main__":
    communication_between_segments()