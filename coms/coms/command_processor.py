import logging
from collections import deque
import time
from byodr.utils import timestamp


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"

#################### Can be of inf size. Potentially dangerous if the user keeps steering => queue keeps appending data ####################
steering_queue = deque() # A queue in which steering values other than 0 will be stored in

time_now = 0.0 # Default values for the current time 
delay = 0.0 # Default values for the delay amount 
use_steering_queue = False # Variable that tells the function when it is time to use the queue for steering values
start_counting_down = False # Variable that tells the function to start counting down. We dont want the function to start counting down unless it receives steering first


def process(movement_command):
    global steering_queue
    global time_now
    global delay
    global use_steering_queue
    global start_counting_down

    
    velocity = movement_command["velocity"] # Velocity of the LD segment in m/s
    velocity = 1 # Testing the delay in m/s
    distance = 5 # Distance between the motors of the current segment and the LD segment in m
    steering = movement_command["steering"] # Getting the steering value from the command we just got
    applied_steering = 0.0 # The steering value that the final command will include
    time_counter = time.perf_counter() # Getting the current time value

    # If we detect that the LD is turning
    if steering != 0:

        # Calculating the delay for steering
        try:
            # Execution delay of steering in s
            # We want the absolute value, the delay is never negative
            delay = abs(distance / velocity)
        except ZeroDivisionError:
            pass

        # Place the non-zero steering in the deque
        steering_queue.append(steering)

        # Getting the time in which we start receiving steering other than 0
        # Making sure we mark the time only once, and not keep updating it every time we receive non-zero steering
        # We will be able to run this again after the current queue with values is emptied.
        if not start_counting_down:
            time_now = time.perf_counter()

        # Telling the function that we received steering, and to start counting down so that the values we store are applied after "delay" seconds
        start_counting_down = True



    # If we need to start counting down
    # AND
    # If the time difference between the function time and the time in which we first received steering is "delay" seconds
    if start_counting_down and time_counter - time_now >= delay:
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
            # If the queue is empty, we put steering = 0 and turn the triggers to False
            applied_steering = 0.0
            use_steering_queue = False
            start_counting_down = False


    # We reverse throttle
    movement_command["throttle"] = -(movement_command["throttle"])

    # We apply the steering.
    movement_command["steering"] = applied_steering

    # Replacing the received command's timestamp with a current one
    movement_command["time"] = timestamp()

    return movement_command