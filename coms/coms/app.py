import argparse
import logging
import multiprocessing
import signal
import threading
from byodr.utils.ssh import Router
from .communication import start_communication
from .common_utils import *
from .robot_comm import *


router = Router()

# This flag starts as false
quit_event = multiprocessing.Event()
quit_event.clear()

signal.signal(signal.SIGINT, lambda sig, frame: _interrupt())
signal.signal(signal.SIGTERM, lambda sig, frame: _interrupt())


# Set the flag as true when we receive interrupt signals
def _interrupt():
    logger.info("Received interrupt, quitting.")
    quit_event.set()


def main():
    # Adding the parser here for a static design pattern between all services
    parser = argparse.ArgumentParser(description="Communication sockets server.")
    parser.add_argument("--name", type=str, default="none", help="Process name.")
    parser.add_argument("--config", type=str, default="/config", help="Config directory path.")
    args = parser.parse_args()

    application = ComsApplication(event=quit_event, config_dir=args.config)
    tel_chatter = TeleopChatter(application.get_robot_config_file(), application.get_user_config_file())
    socket_manager = SocketManager(tel_chatter, quit_event=quit_event)

    # Starting the functions that will allow the client and server of each segment to start sending and receiving data
    communication_thread = threading.Thread(target=start_communication, args=(socket_manager, application.get_robot_config_file()))

    application.setup()
    socket_manager.start_threads()

    # Starting the threads of Coms
    communication_thread.start()

    logger.info("Ready")
    try:
        while not quit_event.is_set():
            socket_manager.get_teleop_chatter()
    finally:
        # Closing the threads when the executions finish
        communication_thread.join()
        socket_manager.join_threads()

    logger.info("Stopped threads in app.py.")
    return 0


if __name__ == "__main__":
    # Declaring the logger
    logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger(__name__)
    main()
