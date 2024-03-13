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
from byodr.utils import timestamp
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

global_watchdog_status_list = []


def read_config_file(config_file_dir, local_ip):
    
    global global_watchdog_status_list
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

    # Getting the amount of segments behind us and making the watchdog status list made up of the local seg and all the segs behind it
    segments_in_robot = len(sections_list) - 1 # We remove 1 because we dont care about the "direction" header
    segments_behind = segments_in_robot - int(local_position)
    global_watchdog_status_list = ['0'] * (segments_behind+1) # We add 1 because the list always includes the local segment

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

    segment_client = Segment_client(follower_ip, nano_port, 0.10) # The client that will connect to a follower
    segment_server = Segment_server(local_ip, nano_port, 0.10) # The server that will wait for the lead to connect

    # Starting the functions that will allow the client and server of each segment to start sending and receiving data
    command_receiver_thread = threading.Thread( target=command_receiver, args=(socket_manager, segment_client, local_ip, head_ip, msg_from_server_queue) )
    client_interface_thread = threading.Thread( target=client_code, args=(socket_manager, segment_client) )
    server_interface_thread = threading.Thread( target=server_code,  args=(segment_server, msg_from_server_queue) )

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
    global global_watchdog_status_list
    previous_command = {'steering': 0.0, 'throttle': 0, 'time': 0, 'navigator': {'route': None}, 'button_b': 1, 'velocity': 0.0}
    stop_counter = 0
    counter = 0

    # The head segment forwards commands from teleop to pilot
    # This block is only used by the Head segment
    if local_ip == head_ip:

        # Getting the local watchdog status
        status_dictionary = socket_manager.get_watchdog_status()
        while status_dictionary is None:
            status_dictionary = socket_manager.get_watchdog_status()

        while not quit_event.is_set():
            time_counter = time.perf_counter()

            # Getting the local watchdog status
            status_dictionary = socket_manager.get_watchdog_status()
            global_watchdog_status_list[0] = status_dictionary.get("status")

            # Receiving the commands that we will process/forward to our FL, from Teleop
            segment_client.msg_to_server = socket_manager.get_teleop_input()
            if segment_client.msg_to_server is not None:
                segment_client.msg_to_server['time'] = timestamp()
                previous_command = segment_client.msg_to_server
            else:
                 previous_command['time'] = timestamp()
                 segment_client.msg_to_server = previous_command
                

            # Forwarding commands to pilot
            socket_manager.publish_to_pilot(segment_client.msg_to_server)

            # if watchdog_status_list[0] == 0:

            #     socket_manager.publish_to_pilot(None)
            #     segment_client.msg_to_server = status_dictionary
            #     # logger.warning(f"[Client] The Pi of the segment is malfunctioning")

            # counter = counter + 1
            # if time_counter - stop_counter >= 1:
            #     print(f"Did {counter} repetitions in 1 second.")
            #     stop_counter = time_counter
            #     counter = 0
            # print(global_watchdog_status_list)

    # All other segments are forwarding commands from the LD COM to pilot
    else:

        # Getting the local watchdog status
        status_dictionary = socket_manager.get_watchdog_status()
        while status_dictionary is None:
            status_dictionary = socket_manager.get_watchdog_status()

        while not quit_event.is_set():
            time_counter = time.perf_counter()

            # Getting the local watchdog status
            status_dictionary = socket_manager.get_watchdog_status()
            global_watchdog_status_list[0] = status_dictionary.get("status")

            # Receiving the commands that we will process/forward to our FL, from our current LD
            try:
                segment_client.msg_to_server = msg_from_server_queue.pop()

                # Storing the previous command to keep sending to Pilot, in case we do not receive new commands from the LD for some time
                previous_command = segment_client.msg_to_server
            
            except IndexError:
                # If the queue is empty, we send the previous command we received from the LD
                segment_client.msg_to_server = previous_command
                # logger.info(f"[Server] Command to publish: {segment_client.msg_to_server}")

            # Replacing the received command's timestamp with a current one.
            # This way, we keep the Pi watchdog alive, because the server might receive commands too late
            segment_client.msg_to_server["time"] = timestamp()
            
            # Forwarding commands to pilot
            socket_manager.publish_to_pilot(segment_client.msg_to_server)

            # if watchdog_status_list[0] == 0:
            #     socket_manager.publish_to_pilot(None)
            #     segment_client.msg_to_server = status_dictionary
            #     # logger.warning(f"[Client] The Pi of the segment is malfunctioning")
            # counter = counter + 1
            # if time_counter - stop_counter >= 1:
            #     print(f"Did {counter} repetitions in 1 second.")
            #     stop_counter = time_counter
            #     counter = 0
            # print(global_watchdog_status_list)


def client_code(socket_manager, segment_client):
    """Use:
        The main functionality of the client of the segment. It will try to connect to its assigned server. If it connects successfully,
        will send and then receive (in that order) data from its assigned server.
        If it loses connection with the server, will automatically try to reconnect every 2 seconds

    Returns:
        Nothing
    """

    global global_watchdog_status_list
    previous_velocity = {'velocity': 0.0}
    counter_client = 0

    
    while not quit_event.is_set():

        # The client will not start unless the command we have from Teleop or our LD is not None
        segment_client.connect_to_server()

        # Start the send/recv cycle only if the socket was successfully made
        while segment_client.socket_initialized:
            time_counter = time.perf_counter()
            counter_client = counter_client + 1

            try:
                ######################################################################################################
                # Main part of the send/recv of the client

                # Getting velocity from the Pi>Vehicle>Coms
                dict_with_velocity = socket_manager.get_velocity()

                if type(dict_with_velocity) is dict and dict_with_velocity['velocity'] != 999.0:
                    previous_velocity = dict_with_velocity
                else:
                    dict_with_velocity = previous_velocity

                segment_client.msg_to_server.update(dict_with_velocity)
                
                # Sending the command to our FL
                if counter_client == 200:
                    print(f"[Client] Abount to send message to server: {segment_client.msg_to_server}")
                segment_client.send_to_FL()

                # Receiving a reply from the FL
                if counter_client == 200:
                    print(f"[Client] Waiting to receive from the server...")
                segment_client.recv_from_FL()
                if counter_client == 200:
                    print(f"[Client] Received message to server: {segment_client.msg_from_server}")

                # Updating the list with the status received from the FL
                global_watchdog_status_list[1:] = segment_client.msg_from_server

                # if counter_client == 200:
                #     logger.info(f"[Client] Watchdog status list: {global_watchdog_status_list}")
            
                ######################################################################################################
                stop_time = time.perf_counter()

                if counter_client == 200:
                    print(f"[Client] A round took {(stop_time-time_counter)*1000:.3f}ms\n\n\n")
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
                logger.exception("[Client] Exception details:")
                break


def server_code(segment_server, msg_from_server_queue):
    """Use:
        The main functionality of the server of the segment. It will setup a socket server and will wait for a client to connect.
        Once a client connects, the server will wait for data, and when it is received, will send back a reply.
        The data received will be appended to a deque. The command receiver thread consumes items from the deque by forwarding commands to the local pilot.

    Returns:
        Nothing
    """

    global global_watchdog_status_list
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
                if counter_server == 200:
                    print(f"[Server] Waiting to receive from the client...")
                segment_server.recv_from_LD()
                
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

                if counter_server == 200:
                    print(f"[Server] Edited message from client: {segment_server.processed_command}")

                # Sending a reply to the LD
                segment_server.msg_to_client = global_watchdog_status_list
                if counter_server == 200:
                    print(f"[Server] About to send to client: {segment_server.msg_to_client}")
                segment_server.send_to_LD()

            ######################################################################################################
                
                stop_time = time.perf_counter()

                if counter_server == 200:
                    print(f"[Server] A round took {(stop_time-time_counter)*1000:.3f}ms\n\n\n")
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