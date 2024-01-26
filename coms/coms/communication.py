import logging
import threading
from collections import deque
import socket
import copy
import time
import multiprocessing
import signal
import configparser
from byodr.utils.ssh import Nano
from .server import Segment_server
from .client import Segment_client
from .command_processor import process
from .common_utils import common_queue


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

robot_config_parser = configparser.ConfigParser()


def read_config_file(config_file_dir, local_ip):
    
    follower_ip = None
    lead_ip = None
    head_ip = None

    # Get the contents of the file
    robot_config_parser.read(config_file_dir)
    sections_list = robot_config_parser.sections()

    # Getting our local position
    for entry in sections_list[1:]:
        if robot_config_parser.get(entry, 'ip.number') == local_ip:
            local_position = robot_config_parser.get(entry, 'position')
            break

    # Getting the IPs of the FL, LD and HD segments
    for entry in sections_list[1:]:
        if robot_config_parser.get(entry, 'position') == str(int(local_position)+1):
            follower_ip = robot_config_parser.get(entry, 'ip.number')

        elif robot_config_parser.get(entry, 'position') == str(int(local_position)-1):
            lead_ip = robot_config_parser.get(entry, 'ip.number')

        elif robot_config_parser.get('direction', 'head') == entry:
            head_ip = robot_config_parser.get(entry, 'ip.number')

    return head_ip, lead_ip, follower_ip


def start_communication(socket_manager, robot_config_dir):
    """Use: 
        The main function that starts all other communicaiton functionalities.
        Starts 3 threads:\n
        1- A thread that will receive commands from TEL or LD-COM, depending on the IP of the device calling the function.\n
        2- A thread that starts the functionalities of the client of the segment.\n
        3- A thread that starts the functionalities of the server of the segment.\n

    Returns:
        0 if all threads started close gracefully.
    """


    # A deque that will store messages received by the server of the segment
    msg_from_server_queue = deque(maxlen=1)

    # Getting the IP of the local machine
    local_ip = Nano.get_ip_address()
    nano_port = 1111

    # Reading the config files to receive information about this and neighboring segments
    head_ip, lead_ip, follower_ip = read_config_file(robot_config_dir, local_ip)

    # Getting the follower/lead IPs from the local IP. (Temporary, until we get a full robot config file)
    follower_ip = "192.168." + str( int(local_ip[8])+1 ) + ".100"

    segment_client = Segment_client(follower_ip, nano_port, 0.10) # The client that will connect to a follower
    segment_server = Segment_server(local_ip, nano_port, 0.10) # The server that will wait for the lead to connect

    # Starting the functions that will allow the client and server of each segment to start sending and receiving data
    command_receiver_thread = threading.Thread( target=command_receiver, args=(socket_manager, segment_client, local_ip, head_ip, msg_from_server_queue) )
    client_interface_thread = threading.Thread( target=client_code, args=(socket_manager, segment_client) )
    server_interface_thread = threading.Thread( target=server_code,  args=(segment_server, msg_from_server_queue) )

    # get data from both files and each coms needs to know to which segment it belongs to 
    # the Segment_client and Segment_server will need to be passed as arguments inside the client and server code threads

    # Starting the threads of Coms
    command_receiver_thread.start()
    client_interface_thread.start()
    server_interface_thread.start()

    # Closing the threads when the executions finish
    command_receiver_thread.join()
    client_interface_thread.join()
    server_interface_thread.join()
    logger.info("Stopped threads in communication.py.")
    return 0


def command_receiver(socket_manager, segment_client, local_ip, head_ip, msg_from_server_queue):
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
   
    watchdog_status_list = []
    status_dictionary = None
    counter_main = 0

    while not quit_event.is_set():

        # The head segment forwards commands from teleop
        # This block is only used by the Head segment
        if local_ip == head_ip:

            watchdog_status_list.extend([0,0])

            while not quit_event.is_set():

                counter_main = counter_main + 1

                # Receiving the commands that we will process/forward to our FL, from Teleop
                # The code will get stuck in this loop, until COM gets non-None type commands from teleop
                segment_client.msg_to_server = socket_manager.get_teleop_input()
                while segment_client.msg_to_server is None:
                    segment_client.msg_to_server = socket_manager.get_teleop_input()



                while status_dictionary is None:
                    status_dictionary = socket_manager.get_watchdog_status()
                watchdog_status_list[0] = status_dictionary.get("status")

                if counter_main == 2000:
                    logger.info(f"[Client] Watchdog status: {watchdog_status_list}")
                    counter_main = 0

                # read_config_file(config_file_dir)

                # Forwarding commands to pilot only if the local Pi is working
                if watchdog_status_list[0] == 1:
                    socket_manager.publish_to_pilot(segment_client.msg_to_server)
                else:
                    socket_manager.publish_to_pilot(None)
                    segment_client.msg_to_server = status_dictionary
                    logger.warning(f"[Client] The Pi of the segment is malfunctioning")



        # All other segments are forwarding commands from the COM server
        else:

            watchdog_status_list.extend([0])

            while not quit_event.is_set():

                counter_main = counter_main + 1

                while status_dictionary is None:
                    status_dictionary = socket_manager.get_watchdog_status()
                watchdog_status_list[0] = status_dictionary.get("status")

                if counter_main == 2000:
                    logger.info(f"[Server] Watchdog status: {watchdog_status_list[0]}")
                    counter_main = 0

                # Receiving the commands that we will process/forward to our FL, from our current LD
                try:
                    segment_client.msg_to_server = msg_from_server_queue.pop()
                
                except IndexError:
                    # If the queue is empty, we do nothing and check again later
                    pass


                # Forwarding commands to pilot only if the local Pi is working
                if watchdog_status_list[0] == 1:
                    socket_manager.publish_to_pilot(segment_client.msg_to_server)
                else:
                    socket_manager.publish_to_pilot(None)
                    segment_client.msg_to_server = status_dictionary
                    # logger.warning(f"[Client] The Pi of the segment is malfunctioning")


def client_code(socket_manager, segment_client):
    """Use:
        The main functionality of the client of the segment. It will try to connect to its assigned server. If it connects successfully,
        will send and then receive (in that order) data from its assigned server.
        If it loses connection with the server, will automatically try to reconnect every 2 seconds

    Returns:
        Nothing
    """

    counter_client = 0

    
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

                dict_with_velocity = socket_manager.get_velocity()
                if dict_with_velocity is None:
                    logger.warning("[Client] Didnt receive velocity from Vehicle")
                    dict_with_velocity = dict(velocity = 0.0)
                
                if "throttle" in segment_client.msg_to_server:
                    segment_client.msg_to_server.update(dict_with_velocity)

                # Sending the command to our FL
                segment_client.send_to_FL()

                # Receiving a reply from the FL
                segment_client.recv_from_FL()

                if counter_client == 50:
                    logger.info(f"[Client] Sent message to server: {segment_client.msg_to_server}")
            
                ######################################################################################################
                stop_time = time.perf_counter()

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


def server_code(segment_server, msg_from_server_queue):
    """Use:
        The main functionality of the server of the segment. It will setup a socket server and will wait for a client to connect.
        Once a client connects, the server will wait for data, and when it is received, will send back a reply.
        The data received will be appended to a deque. The command receiver thread consumes items from the deque by forwarding commands to the local pilot.

    Returns:
        Nothing
    """

    counter_server = 0

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

                # Processing the command before sending it to the FL.
                # Since we might receive a status message instead of a movement command, we check if its a normal movement command first
                if "throttle" in command_to_process:
                    segment_server.processed_command = process(command_to_process)

                    # Placing the message from the server in the queue
                    msg_from_server_queue.append(segment_server.processed_command)


                if counter_server == 50:
                    logger.info(f"[Server] Edited message from client: {segment_server.processed_command}")


                # Sending a reply to the LD
                segment_server.msg_to_client = "1"
                segment_server.send_to_LD()

            ######################################################################################################
                
                stop_time = time.perf_counter()

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