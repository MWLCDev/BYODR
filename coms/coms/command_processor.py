import logging
import threading


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"



def process(movement_command):

    if type(movement_command) is dict:

        # We reverse throttle and inverse steering
        movement_command["throttle"] = -(movement_command["throttle"])
        movement_command["steering"] = -(movement_command["steering"])
