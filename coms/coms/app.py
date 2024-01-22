import logging
import threading
from .communication import communication_between_segments



# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)



def main():
    # Starting the functions that will allow the client and server of each segment to start sending and receiving data
    communication_thread = threading.Thread( target=communication_between_segments )


    # Starting the threads of Coms
    communication_thread.start()

    # Closing the threads when the executions finish
    communication_thread.join()
    logger.info("Stopped thread in app.py.")
    return 0


if __name__ == "__main__":
    main()