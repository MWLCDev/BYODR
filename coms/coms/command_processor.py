from collections import deque
import time


class MovementProcessor:
    """
    A class to process movement commands received from the LD segment.

    This class handles the processing of movement commands, including reversing
    throttle if necessary, updating timestamps, and applying steering values after
    a calculated delay to mimic the movement of the leading segment.
    """

    def __init__(self, distance=1.35):
        """
        Initializes the MovementProcessor with default settings.

        Args:
            distance (float): The distance between the motors of the current segment
                              and the LD segment in meters. Default is 1.35 meters.
        """
        self.steering_queue = deque()  # Queue to store steering values
        self.time_now = 0.0  # Timestamp when steering was first received
        self.delay = 0.0  # Delay before applying steering, calculated based on velocity
        self.distance = distance  # Distance between segments
        self.use_steering_queue = False  # Flag to indicate when to use the steering queue
        self.started_counting_down = False  # Flag to indicate if the delay countdown has started

    def process(self, movement_command):
        """
            Processes the movement command from the LD segment.

             This method is processing commands received from the LD segment. In general, the LD sends us commands that its executing now,
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
        velocity = movement_command["velocity"]
        steering = movement_command["steering"]
        throttle = movement_command["throttle"]
        applied_steering = 0.0
        current_time = time.perf_counter()

        # Clear the steering queue when the robot is standing still
        if throttle == 0:
            self.steering_queue.clear()

        # If the LD is turning, process the steering command
        if steering != 0:
            if velocity != 0:
                # Calculate the delay based on distance and velocity
                self.delay = abs(self.distance / velocity)
                # Store the steering value for later application
                self.steering_queue.append(steering)
                # Start the delay countdown if not already started
                if not self.started_counting_down:
                    self.time_now = current_time
                    self.started_counting_down = True
            else:
                # If velocity is zero, reverse throttle and steering immediately
                movement_command["throttle"] = -throttle
                movement_command["steering"] = -steering
                return movement_command

        # Check if the delay period has passed to apply steering from the queue
        if self.started_counting_down and (current_time - self.time_now >= self.delay):
            self.use_steering_queue = True
            self.started_counting_down = False

        # Apply steering from the queue if it's time
        if self.use_steering_queue:
            try:
                applied_steering = self.steering_queue.popleft()
            except IndexError:
                # If the queue is empty, stop using the steering queue
                applied_steering = 0.0
                self.use_steering_queue = False

        # Reverse throttle (if the segment is mounted backwards)
        movement_command["throttle"] = -throttle
        # Apply the delayed steering value
        movement_command["steering"] = -applied_steering

        return movement_command
