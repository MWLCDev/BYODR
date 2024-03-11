import logging
from collections import deque
import time


# Declaring the logger
logger = logging.getLogger(__name__)
log_format = "%(levelname)s: %(filename)s %(funcName)s %(message)s"


############################################################################################################################################
#################### Can be of inf size. Potentially dangerous if the user keeps steering => queue keeps appending data ####################
steering_queue = deque() # A queue in which steering values other than 0 will be stored in
############################################################################################################################################

time_now = 0.0 # Default values for the current time 
delay = 0.0 # Default values for the delay amount 
distance = 1.8 # Distance between the motors of the current segment and the LD segment in m
use_steering_queue = False # Variable that tells the function when it is time to use the queue for steering values
started_counting_down = False # Variable that tells the function to start counting down. We dont want the function to start counting down unless it receives steering first


def process(movement_command):
    """Use:
        This function is processing commands received from the LD segment. In general, the LD sends us commands that its executing now,
        and it is the FL's job to decide what to do based on those received commands.

        - Will reverse throttle, if the segment is mounted backwards, compared to its LD. All throttle values are applied right away\n
        - Will update the timestamp in the command received, so as not to keep the timestamp of the Head segment for all other segments.
        Each segment checks the timestamp in the command. If the command timestamp is too old, it wont get forwarded, so we need to update 
        the timstamp value with the value of the time of retrieval from the LD.\n
        - Will apply the steering received from the LD. If steering is 0, then nothing to do. If steering is not 0, then it will start a special process.
        Firstly, it will calculate the delay that it needs to wait before applying the steering values. 
        This delay is calculated as: 'Delay = Distance_between_segment_motors / Velocity of LD segment'.
        Secondly, the steering values that are not 0 are stored in a deque, to keep track of what the segment needs to apply after the delay.
        Thirdly, a countdown starts. After 'delay' seconds pass, then the segment will start applying the steering values stored in the queue,
        effectively turning the segment exactly the same way as the LD did 'delay' seconds ago.
        When the queue is empty, meaning that it has finished turning like its LD did, it will continue moving straight.

    Args:
        movement_command (Dictionary): {'steering': Float, 'throttle': Float, 'time': Int, 'navigator': {'route': None}, 'velocity': Float}

    Returns:
        Dictionary: {'steering': Float, 'throttle': Float, 'time': Int, 'navigator': {'route': None}, 'velocity': Float}
    """


    global steering_queue
    global time_now
    global delay
    global use_steering_queue
    global started_counting_down

    
    velocity = movement_command["velocity"] # Velocity of the LD segment in m/s
    # velocity = 1 # Testing the delay in m/s
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

        # If velocity == 0, meaning the robot is standing still, we do not move on with calculations
        except ZeroDivisionError:

            # We reverse throttle
            movement_command["throttle"] = (movement_command["throttle"])

            # We apply the steering.
            movement_command["steering"] = -movement_command["steering"]

            return movement_command

        # Place the non-zero steering in the deque
        steering_queue.append(steering)

        # Getting the time in which we start receiving steering other than 0
        # Making sure we mark the time only once, and not keep updating it every time we receive non-zero steering
        # We will be able to run this again after the current queue with values is emptied.
        if not started_counting_down:
            time_now = time.perf_counter()

        # Telling the function that we received steering, and to start counting down so that the values we store are applied after "delay" seconds
        started_counting_down = True



    # If we need to start counting down
    # AND
    # If the time difference between the function time and the time in which we first received steering is "delay" seconds
    # print(time_counter - time_now)
    if started_counting_down and time_counter - time_now >= delay:
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
            # print("popped")
        except IndexError:
            # If the queue is empty, we put steering = 0 and turn the triggers to False
            applied_steering = 0.0
            use_steering_queue = False
            started_counting_down = False


    # We reverse throttle
    movement_command["throttle"] = (movement_command["throttle"])

    # We apply the steering.
    movement_command["steering"] = applied_steering

    return movement_command