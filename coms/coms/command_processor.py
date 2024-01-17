import logging
from byodr.utils import timestamp


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"



def process(movement_command):

    # We reverse throttle
    # Steering remains the same
    movement_command["throttle"] = -(movement_command["throttle"])

    # Replacing the received command's timestamp with a current one
    movement_command["time"] = timestamp()

    return movement_command