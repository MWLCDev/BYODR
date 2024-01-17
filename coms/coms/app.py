import logging
import multiprocessing
import threading
import queue
import socket
import copy
import signal
import time
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.ssh import Nano
from .server import Segment_server
from .client import Segment_client
from .command_processor import process

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

# A queue that will store messages received by the server of the segment
msg_from_server_queue = queue.Queue(maxsize=1)

# Declaring the inter-service sockets
# Other socket located on pilot/app.py/140
# Socket that forwards movement commands to Pilot
coms_to_pilot_publisher = JSONPublisher(url="ipc:///byodr/coms_to_pilot.sock", topic="aav/coms/input")

# Other socket located on teleop/app.py/306
# Socket that receives movement commands from Teleop
teleop_receiver = json_collector(url='ipc:///byodr/teleop_to_coms.sock', topic=b'aav/teleop/input', event=quit_event)

# Other socket located on vehicles/rover/app.py/34
# Socket that receives velocity from Vehicle
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

    # Starting the threads of Coms
    client_interface_thread.start()
    server_interface_thread.start()


    ######################################################################################################
    # In this block, Coms receives commands from teleop, and also forwards commands to Pilot
    # In between receiving from teleop and sending to pilot,
    # the client_interface_thread and server_interface_thread edit the value of the command that is about to be sent to pilot

    while not quit_event.is_set():

        # The head segment forwards commands from teleop
        # This block is only used by the Head segment
        if local_ip == "192.168.1.100":
            while not quit_event.is_set():

                # Receiving the commands that we will process/forward to our FL, from Teleop
                # The code will get stuck in this loop, until COM gets non-None type commands from teleop
                segment_client.msg_to_server = teleop_receiver.get()
                while segment_client.msg_to_server is None:
                    segment_client.msg_to_server = teleop_receiver.get()


                # Forwarding commands to pilot
                coms_to_pilot_publisher.publish(segment_client.msg_to_server)



        # All other segments are forwarding commands from the COM server
        else:
            while not quit_event.is_set():

                # Receiving the commands that we will process/forward to our FL, from our current LD
                try:

                    # Using get() will make the command wait for a data packet to be availabie in the queue, so that it can be retrieved
                    # Using get_nowait() will make the command get whatever is inside, and if its empty, it raises an exception (except queue.Empty)
                    segment_client.msg_to_server = msg_from_server_queue.get_nowait()

                
                except queue.Empty:
                    # If the queue is empty, we will wait for the queue to be full
                    # segment_client.msg_to_server = msg_from_server_queue.get()
                    pass


                # Forwarding commands to pilot
                coms_to_pilot_publisher.publish(segment_server.processed_command)


    ######################################################################################################


    # Closing the threads when the executions finish
    client_interface_thread.join()
    server_interface_thread.join()
    logger.info("Stopped threads.")
    return 0


def client_code():
    counter_client = 0
    # time_stop = 0

    
    while not quit_event.is_set():

        # The client will not start unless the command we have from Teleop or our LD is not None
        if segment_client.msg_to_server is not None:
            segment_client.connect_to_server()

        # Start the send/recv cycle only if the socket was successfully made
        while segment_client.socket_initialized:
            time_counter = time.perf_counter()
            counter_client = counter_client + 1

            try:

                ######################################################################################################
                # Main part of the send/recv of the client

                # Sending the command to our FL
                segment_client.send_to_FL()

                # Receiving a reply from the FL
                segment_client.recv_from_FL()

                # if time_counter - time_stop >= 1:
                #     # logger.info(f"[Client] Got reply from server: {segment_client.msg_from_server}")
                #     logger.info(f"[Client] Sent message to server: {segment_client.msg_to_server}")
                if counter_client == 200:
                    logger.info(f"[Client] Sent message to server: {segment_client.msg_to_server}")

                    
            
                ######################################################################################################
                stop_time = time.perf_counter()
                # if time_counter - time_stop >= 1:
                #     print(f"[Client] {counter_client} rounds in 1 second")
                #     counter_client = 0
                #     time_stop = time_counter

                if counter_client == 200:
                    logger.info(f"[Client] Got reply from server: {segment_client.msg_from_server}")
                    logger.info(f"[Client] A round took {(stop_time-time_counter)*1000:.3f}ms\n")
                    counter_client = 0

            # Catching potential exceptions and attempting to reconnect each time
            except ConnectionResetError:
                # logger.error("[Client] Server disconnected")
                break
                
            except socket.timeout:
                # logger.error("[Client] 100ms passed without receiving data from the server")
                break

            except Exception as e:
                # logger.error(f"[Client] Got error during communication: {e}")
                break


def server_code():
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
                if counter_server == 200:
                    logger.info(f"[Server] Received from client: {segment_server.msg_from_client}")

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
                    # Using put() will make the command wait for a free spot on the queue.
                    # Using put_nowait() will make the command add the data in the queue and raise an exception if its already full (except queue.Full)
                    try:
                        msg_from_server_queue.put_nowait(segment_server.processed_command)
                    
                    except queue.Full:
                        pass

                if counter_server == 200:
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

                if counter_server == 200:
                    logger.info(f"[Server] Sent reply to client: {segment_server.msg_to_client}")
                    logger.info(f"[Server] A round took {(stop_time-time_counter)*1000:.3f}ms\n")
                    counter_server = 0

            # Catching potential exceptions and exiting the communication loop
            except socket.timeout:
                # logger.error("[Server] 100ms passed without receiving data from the client")
                break

            except ConnectionResetError:
                # logger.error("[Server] Client disconnected.")
                break

            except Exception as e:
                # logger.error(f"[Server] Got error during communication: {e}")
                break


if __name__ == "__main__":
    main()