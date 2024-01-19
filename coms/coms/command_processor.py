import logging
from collections import deque
import time
from byodr.utils import timestamp


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"

# A queue in which steering values other than 0 will be stored in
steering_queue = deque()

# Default values for the current time and delay time
time_now = 0.0
delay = 0.0

# Variable that tells the function when it is time to use the queue for steering values
use_steering_queue = False



def process(movement_command):
    global steering_queue
    global time_now
    global delay
    global use_steering_queue

    # Velocity of the LD segment in m/s
    # The Pi gives the velocity to Vehicles from servos.py L407 -> core.py L165
    velocity = movement_command["velocity"]

    # Testing the delay
    velocity = 1 # in m/s
    
    # Distance between the motors of the current segment and the LD segment in m
    distance = 1

    # Getting the steering value from the command we just got
    steering = movement_command["steering"]

    # The steering value that the final command will include
    applied_steering = 0.0


    # If we detect that the LD is turning
    if steering != 0:

        # Calculating the delay for steering
        try:
            # Execution delay of steering in s
            # We want the absolute value, the delay is never negative
            delay = abs(distance / velocity)

        except ZeroDivisionError:
            delay = 0.0

        # Place the non-zero steering in the deque
        steering_queue.append(steering)


    # Getting the current time value
    time_counter = time.perf_counter()

    # If its time to start applying the steering values
    if time_counter - time_now >= delay:

        # We mark the time we start applying the values for the next iteration of the function
        time_now = time_counter

        # We turn the trigger into True, making the function use steering from the queue
        use_steering_queue = True

    # Trigger that tells the function to use steering from the queue
    if use_steering_queue:
        # We take the first item in the deque and we apply it in the processed movement command
        # Since we will first apply the steering that was first added to the deque (oldest steering first),
        # our data structure needs to be FIFO (First in First out)
        try:
            applied_steering = steering_queue.popleft()
        except IndexError:
            # If the queue is empty, we put steering = 0 and turn the trigger to False
            applied_steering = 0.0
            use_steering_queue = False


    # We reverse throttle
    movement_command["throttle"] = -(movement_command["throttle"])

    # We apply the steering.
    movement_command["steering"] = applied_steering

    # Replacing the received command's timestamp with a current one
    movement_command["time"] = timestamp()

    return movement_command