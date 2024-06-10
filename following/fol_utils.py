import configparser
import glob
import logging
import multiprocessing
import os
import threading
import time

import cv2
import numpy as np
from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher
from byodr.utils.option import parse_option
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class FollowingController:
    def __init__(self, model_path, user_config_args):
        self.user_config_args = user_config_args
        self.model = YOLO(model_path)
        self.no_human_counter = 0
        self.clear_path = 4
        self.current_throttle = 0
        self.current_steering = 0
        self.current_spin = None
        self.current_camera_pan = 0
        self.current_method = "Absolute"
        self.image_counter = 0
        self.prev_time = int(timestamp())
        self.image_save_path = "/byodr/yolo_person"
        self.camera_following_flag = 0
        self.going_home_flag = 0
        self.last_azimuth = 0
        self.teleop_chatter = None
        self.publisher = None
        self.request_check_thread = None
        self.run_yolo_inf = None
        self.stop_yolo = threading.Event()  # Event to signal the YOLO thread to stop
        self.stop_threads = False

        self.get_fol_configs()

        os.makedirs(self.image_save_path, exist_ok=True)

    def get_fol_configs(self):
        self.screen_center = parse_option("following.screen.center", int, 320, [], **self.user_config_args)
        self.center_offset = parse_option("following.center.offset", int, 0, [], **self.user_config_args)
        self.second_offset = parse_option("following.center.offset", int, 80, [], **self.user_config_args)
        self.third_offset = parse_option("following.center.offset", int, 80, [], **self.user_config_args)
        self.pan_offset = parse_option("following.center.offset", int, 50, [], **self.user_config_args)
        self.start_height = parse_option("following.center.offset", int, 340, [], **self.user_config_args)
        # Detected person is too close to the robot if the height is too large
        self.unsafe_height = parse_option("following.unsafe.height", int, 360, [], **self.user_config_args)
        self.max_human_absence_frames = parse_option("following.center.offset", int, 5, [], **self.user_config_args)
        self.min_clear_path_frames = parse_option("following.center.offset", int, 3, [], **self.user_config_args)
        self.smooth_control_step = parse_option("following.center.offset", float, 0.1, [], **self.user_config_args)

    def run(self):
        self.request_check_thread = threading.Thread(target=self.request_check)
        self.publish_command(self.current_throttle, self.current_steering, self.current_spin, self.current_camera_pan, self.current_method)  # Initializing with safe values
        bottom_camera_uri = parse_option("camera.rear.camera.ip", str, "192.168.1.65", [], **self.user_config_args)
        stream_uri = f"rtsp://user1:HaikuPlot876@{bottom_camera_uri}:554/Streaming/Channels/103"
        logger.info("Loading Yolov8 model")
        self.results = self.model.track(source=stream_uri, classes=0, stream=True, persist=True, verbose=False)  # Image recognition with assigning IDs to objects
        logger.info("Yolov8 model loaded")

    def request_check(self):
        """Constantly fetches the request from Teleop"""
        while True:
            time.sleep(0.05)
            try:
                follow_request = self.teleop_chatter()
                if follow_request is None:
                    continue
                if follow_request.get("following") == "Start Following":
                    # Make sure there is only one generator running from YOLO inf
                    if self.run_yolo_inf is None or not self.run_yolo_inf.is_alive():
                        self.publish_command(self.current_throttle, self.current_steering, self.current_spin, self.current_camera_pan, self.current_method)  # Initializing with safe values
                        self.reset_tracking_session()
                        self.stop_threads = False
                        self.run_yolo_inf = threading.Thread(target=self.control_logic, args=(lambda: self.stop_threads,))
                        self.run_yolo_inf.start()
                elif follow_request.get("following") == "Stop Following":
                    logger.info("Stopping Following")
                    self.current_throttle = 0
                    self.current_steering = 0
                    self.current_spin = None
                    self.current_camera_pan = 0
                    self.current_method = "Absolute"
                    self.camera_following_flag = 0
                    self.going_home_flag = 0
                    self.publish_command(self.current_throttle, self.current_steering, self.current_spin, self.current_camera_pan, self.current_method)
                    if self.run_yolo_inf is not None and self.run_yolo_inf.is_alive():
                        self.stop_threads = True  # Set the stop flag
                        self.run_yolo_inf.join()  # Wait for the YOLO thread to stop
            except Exception as e:
                logger.error(f"Exception in request_check: {e}")

    def control_logic(self, stop):
        """Processes each frame of YOLO output."""
        for r in self.results:  # Running the loop for each frame of the stream
            if stop():
                logger.info("YOLO model stopped")
                break
            boxes = r.boxes.cpu().numpy()  # List of bounding boxes in the frame
            self.clear_path = self.check_obstacles(boxes)  # Checking for obstructions
            throttle, steering, spin, camera_pan, method = self.decide_control(boxes)
            self.track_and_save_image(r)
            self.publish_command(throttle, steering, spin, camera_pan, method)  # Sending calculated control commands

    def decide_control(self, boxes):
        """Calculates control commands based on the operator's position on the screen"""
        throttle, steering, spin, camera_pan, method = 0, 0, None, 0, "Absolute"  # No movement by default
        
        # No people detected in the frame
        if not boxes.xyxy.size:  
            self.no_human_counter += 1
            # logger.info(f"No person detected for: {self.no_human_counter} frames")
            if self.no_human_counter >= self.max_human_absence_frames:
                self.current_throttle = throttle
                self.current_steering = steering
                self.current_spin = spin
                self.current_camera_pan = camera_pan
                self.current_method = method
                return throttle, steering, spin, camera_pan, method
            else:
                try:
                    return self.current_throttle, self.current_steering, self.current_spin, self.current_camera_pan, self.current_method  # Passing the previous control command if it exists
                except Exception as e:
                    logger.warning("Exception fetching control commands: " + str(e) + "\n")
                    return 0, 0, None, 0, "Absolute"

        self.no_human_counter = 0  # Resetting the counter if a person is detected
        for box in boxes:  # Checking every detected person in the frame
            try:
                if box.id == boxes.id[0]:  # Get the first ID if it was assigned
                    x1, y1, x2, y2 = box.xyxy[0, :]
                    box_center = (x1 + x2) / 2
                    box_height = y2 - y1
                    box_width = x2 - x1
                    logger.info(f"Box center: {int(box_center)}, Box height: {int(box_height)}")
            except Exception as e:
                logger.warning("Exception tracking: " + str(e) + "\n")
                if (box.xyxy == boxes.xyxy[0]).all:  # Get the first result on the list if ID was not assigned (first result has most confidence)
                    x1, y1, x2, y2 = box.xyxy[0, :]
                    box_center = (x1 + x2) / 2
                    box_height = y2 - y1
                    box_width = x2 - x1
                    logger.info(f"Box center: {int(box_center)}, Box height: {int(box_height)}")

            # Smaller bbox height means the detected person is further away from the camera
            if box_height <= self.start_height:  # Starting movement if person is far enough
                throttle = max(0.2, min(1, ((-(0.01) * box_height) + 3.6)))  # 0.2 at 340p height; 1 at 260p height

            if self.clear_path <= self.min_clear_path_frames:
                # logger.info(f"Path obstructed, only spinning allowed") # No movement if too few frames with clear path passed or too many frames without any detection
                throttle = 0

            if self.camera_following_flag == 1:
                print("camera position taking over")
                throttle, steering, spin, camera_pan, method = self.camera_following(box_center)

            else:
                # Keeping the user in the center of the camera view
                if box_center < (self.screen_center - self.center_offset):  # left = negative steering
                    steering = min(0, max(-0.1, (0.00125 * box_center - 0.4)))  # 0 at 320p; 0.1 at 240p
                    if box_center < (self.screen_center - self.center_offset - self.second_offset):
                        steering = min(-0.1, max(-0.6, (0.004375 * box_center - 1.15)))  # 0.1 at 400p; 0.8 at 560 (forcing max 0.5)
                        # steering = steering*(1.2-throttle)                        # Max steering is scaled down proportionally to the throttle value, max steering = 0.16 at throttle = 1
                        if throttle == 0 or box_center < (self.third_offset):  # Turning in place
                            throttle, steering, spin = self.spin_robot(steering)
                    steering = steering * (1.15 - throttle * 0.75)  # Max steering is scaled down proportionally to the throttle value, max steering = 0.32 at throttle = 1

                elif box_center > (self.screen_center + self.center_offset):  # right = positive steering
                    steering = max(0, min(0.1, (0.00125 * box_center - 0.4)))  # 0 at 320p; 0.1 at 400p
                    if box_center > (self.screen_center + self.center_offset + self.second_offset):
                        steering = max(0.1, min(0.6, (0.004375 * box_center - 1.65)))  # 0.1 at 400p; 0.8 at 560 (forcing max 0.5)
                        if throttle == 0 or box_center > (640 - self.third_offset):
                            throttle, steering, spin = self.spin_robot(steering)
                    # steering = steering*(1.2-throttle)                    # Max steering is scaled down proportionally to the throttle value, max steering = 0.16 at throttle = 1
                    steering = steering * (1.15 - throttle * 0.75)  # Max steering is scaled down proportionally to the throttle value, max steering = 0.32 at throttle = 1

                if abs(box_center - self.screen_center) >= (self.screen_center - self.third_offset):
                    logger.info("Operator on the far side")
                    self.camera_following_flag = 1
                    throttle, steering, spin, camera_pan, method = self.camera_following(box_center)

        self.smooth_controls(throttle, steering)  # Smoothing the movement if the commands are immediately large
        self.current_spin = spin
        self.current_camera_pan = camera_pan
        self.current_method = method
        return self.current_throttle, self.current_steering, self.current_spin, self.current_camera_pan, self.current_method

    def reset_tracking_session(self):
        """Reset the image counter and clear all images in the directory."""
        self.image_counter = 0
        for existing_file in os.listdir(self.image_save_path):
            os.remove(os.path.join(self.image_save_path, existing_file))
        logger.info("Tracking session reset: Image counter zeroed and folder cleared.")

    def track_and_save_image(self, result):
        """Tracks objects in video stream and saves the latest image with annotations."""
        # https://github.com/ultralytics/ultralytics/issues/1696#issuecomment-1948021841
        full_annotated_image = result.plot(show=False, pil=False)  # Ensuring it returns a numpy array
        full_annotated_image = cv2.cvtColor(full_annotated_image, cv2.COLOR_RGB2BGR)  # Convert RGB to BGR for OpenCV
        filename = os.path.join(self.image_save_path, f"image_{self.image_counter}.jpg")
        cv2.imwrite(filename, full_annotated_image)
        self.image_counter += 1

        # Check the number of images in the directory and delete the oldest if more than 10
        all_images = sorted(os.listdir(self.image_save_path), key=lambda x: os.path.getctime(os.path.join(self.image_save_path, x)))

        if len(all_images) > 10:
            oldest_image = all_images[0]
            os.remove(os.path.join(self.image_save_path, oldest_image))

    def publish_command(self, throttle=0, steering=0, spin=None, camera_pan=0, method="Momentary"):
        """Publishes the control commands to Teleop."""
        cmd = {"throttle": throttle, "steering": steering, "spin": spin}
        if camera_pan is not None:
            cmd["camera_pan"] = camera_pan
            cmd["method"] = method
        self.publisher.publish(cmd)
        logger.info(f"Sending command to teleop: {cmd}")
        # print((int(timestamp()) - self.prev_time) / 1000, "ms between messages")
        # self.prev_time = timestamp()

    def check_obstacles(self, boxes):
        """Checks the height of all detected objects and only lets the robot spin if anything is in close proximity.
        Allows regular movement if the path has been clear for more than 3 frames."""
        clear_path = self.clear_path
        for box in boxes:  # Checking every detected person in the frame
            x1, y1, x2, y2 = box.xyxy[0, :]
            if (y2 - y1) >= self.unsafe_height:
                return 0
        clear_path += 1  # Path is clear in this frame
        return clear_path

    def smooth_controls(self, target_throttle, target_steering):
        """Smoothens the acceleration. Unlike the 'mobile controller smoothing', this only works when throttle is increasing."""
        if self.current_throttle <= (target_throttle - self.smooth_control_step):  # Smoothing only if the difference is greater than the control step
            self.current_throttle += self.smooth_control_step
        else:
            self.current_throttle = target_throttle  # Passing without smoothing if the difference is too small
        self.current_steering = target_steering  # steering is not being smoothed

    def spin_robot(self, steering):
        """Makes the wheels of the robot turn in opposite directions. The 'spin' flag decides which turn the robot will spin. 1 = turning right, -1 = turning left.
        The speed of turning is determined by throttle. Steering must always be 0 when using 'spin' flag"""
        spin = int(np.sign(steering))
        throttle = max(0.1, min(0.3, (abs(steering)) / 2))
        steering = 0
        return throttle, steering, spin

    def going_home(self, azimuth, box_center):
        """Moves the camera back to the home position and turns the robot in the opposite direction to camera movement"""
        if abs(box_center - self.screen_center) >= (self.screen_center - self.third_offset):
            self.going_home_flag = 0
            throttle, steering, spin, camera_pan, method = self.camera_following(box_center)
        else:
            if 2500 <= azimuth <= 3550 - self.pan_offset:
                camera_pan = 50
                method = "Momentary"
                steering = -0.4
                throttle, steering, spin = self.spin_robot(steering)
            elif self.pan_offset <= azimuth <= 1000:
                camera_pan = -50
                method = "Momentary"
                steering = 0.4
                throttle, steering, spin = self.spin_robot(steering)

            if self.pan_offset >= azimuth >= 0 or 3550 >= azimuth >= 3550 - self.pan_offset:
                camera_pan = 0
                method = "Absolute"
                spin = None
                throttle = 0
                steering = 0
                self.going_home_flag = 0
                self.camera_following_flag = 0

        return throttle, steering, spin, camera_pan, method

    def camera_following(self, box_center):
        """Calculates control commands based on the 'azimuth' values of the camera."""
        throttle, steering, spin, camera_pan, method = 0, 0, None, None, "Absolute"  # No movement by default
        try:
            self.last_azimuth = azimuth = int(self.request["camera_azimuth"])
            print("fetched azimuth:", azimuth)
        except:
            azimuth = self.last_azimuth
            print("last azimuth:", azimuth)
        if box_center is not None:

            if self.going_home_flag == 1:
                throttle, steering, spin, camera_pan, method = self.going_home(azimuth, box_center)

            else:
                # print("box center:",box_center)
                # Keeping the user in the center of the camera view
                if box_center < (self.screen_center - self.pan_offset) and ((1000 > azimuth >= 0) or (3550 >= azimuth > 3050)):  # ugly
                    camera_pan = int(min(-30, max(-52, (0.1 * box_center - 60))))  # -30 at 300p, -53 at 80p
                    # camera_pan = -50
                    method = "Momentary"
                    if box_center < 320 - self.third_offset and ((1000 > azimuth >= 0) or (3550 >= azimuth > 3050)):
                        steering = -0.25
                        throttle, steering, spin = self.spin_robot(steering)

                elif box_center > (self.screen_center + self.pan_offset) and ((500 > azimuth >= 0) or (3550 >= azimuth > 2500)):
                    camera_pan = int(max(30, min(52, (0.1 * box_center - 4))))  # 20 at 340p, 64 at 560p
                    # camera_pan = 50
                    method = "Momentary"
                    if box_center > 320 + self.third_offset and ((500 > azimuth >= 0) or (3550 >= azimuth > 2500)):
                        steering = 0.25
                        throttle, steering, spin = self.spin_robot(steering)

                if 320 - self.third_offset <= box_center <= 320 + self.third_offset:
                    print("going home")
                    self.going_home_flag = 1
                    throttle, steering, spin, camera_pan, method = self.going_home(azimuth, box_center)

        return throttle, steering, spin, camera_pan, method
