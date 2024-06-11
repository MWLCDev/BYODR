import logging
import os
import threading
import time

import cv2
from byodr.utils.ipc import JSONPublisher
from byodr.utils.option import parse_option
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class YoloInference:
    """Handles everything related to YOLO inference and obtaining detection results."""

    def __init__(self, model_path, user_config_args):
        self.user_config_args = user_config_args
        self.model = YOLO(model_path)
        self.image_save_path = "/byodr/yolo_person"
        self.image_counter = 0
        self.results = None

        os.makedirs(self.image_save_path, exist_ok=True)

    def run(self):
        stream_uri = self.get_stream_uri()
        logger.info("Loading Yolov8 model")
        self.results = self.model.track(source=stream_uri, classes=0, stream=True, conf=0.35, persist=True, verbose=False)
        logger.info("Yolov8 model loaded")

    def get_stream_uri(self):
        bottom_camera_uri = parse_option("camera.front.camera.ip", str, "192.168.1.64", [], **self.user_config_args)
        return f"rtsp://user1:HaikuPlot876@{bottom_camera_uri}:554/Streaming/Channels/103"

    def track_and_save_image(self, result):
        """Tracks objects in video stream and saves the latest image with annotations."""
        full_annotated_image = result.plot(show=False, pil=False)
        full_annotated_image = cv2.cvtColor(full_annotated_image, cv2.COLOR_RGB2BGR)
        filename = os.path.join(self.image_save_path, f"image_{self.image_counter}.jpg")
        cv2.imwrite(filename, full_annotated_image)
        self.image_counter += 1

        all_images = sorted(os.listdir(self.image_save_path), key=lambda x: os.path.getctime(os.path.join(self.image_save_path, x)))
        if len(all_images) > 10:
            oldest_image = all_images[0]
            os.remove(os.path.join(self.image_save_path, oldest_image))

    def reset_tracking_session(self):
        """Reset the image counter and clear all images in the directory."""
        self.image_counter = 0
        for existing_file in os.listdir(self.image_save_path):
            os.remove(os.path.join(self.image_save_path, existing_file))
        logger.info("Tracking session reset: Image counter zeroed and folder cleared.")


class CommandController:
    """Handles command calculations and publishes them."""

    def __init__(self, user_config_args):
        self.user_config_args = user_config_args
        self.current_throttle = 0
        self.current_steering = 0
        self.current_camera_pan = 0
        self.current_azimuth = 0
        self.person_height = 0
        self.publisher = None

        self.get_fol_configs()

    def get_fol_configs(self):
        self.pan_movement_speed = parse_option("camera.pan_movement_speed", int, 6, [], **self.user_config_args)
        # This is when the camera should start moving to follow the user. it is between 0 and 35% of the frame
        self.left_red_zone = parse_option("following.left_red_zone", float, 0.35, [], **self.user_config_args)
        self.right_red_zone = parse_option("following.right_red_zone", float, 0.65, [], **self.user_config_args)
        self.start_height = parse_option("following.center.offset", int, 340, [], **self.user_config_args)

    def update_control_commands(self, persons):
        """Updates camera pan, steering, and throttle based on the operator's position on the screen."""
        for person in persons:
            try:
                self.person_height = person.xywh[0][3]
                # The horizontal position of the detected person's bounding box center within the frame
                x_center_percentage = person.xywhn[0][0]

                self.current_camera_pan = self.calculate_camera_pan(x_center_percentage)
                self.current_steering = self.calculate_steering(x_center_percentage)
                self.current_throttle = self.calculate_throttle()

                if not (0 <= self.current_azimuth <= 500 or 3050 <= self.current_azimuth <= 3550):
                    azimuth_steering_adjustment = self.calculate_azimuth_steering_adjustment()
                    self.current_steering += azimuth_steering_adjustment
                    self.current_camera_pan -= azimuth_steering_adjustment

                break  # Only process the first detected person
            except Exception as e:
                logger.warning(f"Exception updating control commands: {e}")

    def calculate_throttle(self):
        if self.person_height <= self.start_height:
            return max(0.2, min(1, ((-(0.01) * self.person_height) + 3.6)))  # 0.2 at 340p height; 1 at 260p height
        return 0

    def calculate_camera_pan(self, x_center_percentage):
        if x_center_percentage < self.left_red_zone:
            return -self.calculate_pan_adjustment(x_center_percentage)
        elif x_center_percentage > self.right_red_zone:
            return self.calculate_pan_adjustment(x_center_percentage)
        else:
            if self.current_camera_pan != 0:
                if self.current_camera_pan > 0:
                    return -2
                else:
                    return 2
        return 0

    def calculate_pan_adjustment(self, x_center_percentage):
        # Extreme edges
        if x_center_percentage < 0.125 or x_center_percentage > 0.875:
            return self.pan_movement_speed + 4
        # Near edges
        elif x_center_percentage < 0.2 or x_center_percentage > 0.8:
            return self.pan_movement_speed + 2
        else:
            return self.pan_movement_speed

    def calculate_steering(self, x_center_percentage):
        if x_center_percentage < self.left_red_zone:
            return -1 + (x_center_percentage / self.left_red_zone)
        elif x_center_percentage > self.right_red_zone:
            return (x_center_percentage - self.right_red_zone) / (1 - self.right_red_zone)
        else:
            return 0

    def calculate_azimuth_steering_adjustment(self):
        if self.current_azimuth < 500:
            return (500 - self.current_azimuth) / 500
        elif self.current_azimuth > 3050:
            return (3050 - self.current_azimuth) / 500
        else:
            return 0

    def publish_command(self, throttle=0, steering=0, camera_pan=0, spin=None, method="Momentary"):
        """Publishes the control commands to Teleop."""
        # Limiting throttle and steering to 3 decimal places
        throttle = round(throttle, 3)
        steering = round(steering, 3)

        cmd = {"throttle": throttle, "steering": steering, "spin": spin, "button_b": 1}
        if camera_pan is not None:
            cmd["camera_pan"] = camera_pan
            cmd["method"] = method

        self.publisher.publish(cmd)
        logger.info(f'Sending command to teleop: T:{cmd["throttle"]}, S:{cmd["steering"]}, C_P:{cmd.get("camera_pan", "N/A")}')

    def reset_control_commands(self):
        self.current_throttle = 0
        self.current_steering = 0
        self.current_camera_pan = 0
        self.publish_command(self.current_throttle, self.current_steering, self.current_camera_pan)


class FollowingController:
    """Coordinates between `YoloInference` and `CommandController`."""

    def __init__(self, model_path, user_config_args):
        self.yolo_inference = YoloInference(model_path, user_config_args)
        self.command_controller = CommandController(user_config_args)
        self.command_controller.publisher = None
        self.run_yolo_inf = None
        self.stop_threads = False
        self.stop_yolo = threading.Event()

    def run(self):
        threading.Thread(target=self.request_check).start()
        self.command_controller.publish_command(self.command_controller.current_throttle, self.command_controller.current_steering, self.command_controller.current_camera_pan)
        self.yolo_inference.run()

    def request_check(self):
        """Constantly fetches the request from Teleop"""
        while True:
            time.sleep(0.05)
            try:
                follow_request = self.teleop_chatter()
                if follow_request is None:
                    continue
                if follow_request.get("following") == "Start Following":
                    if self.run_yolo_inf is None or not self.run_yolo_inf.is_alive():
                        self.command_controller.publish_command(self.command_controller.current_throttle, self.command_controller.current_steering, self.command_controller.current_camera_pan)
                        self.yolo_inference.reset_tracking_session()
                        self.stop_threads = False
                        self.run_yolo_inf = threading.Thread(target=self.control_logic, args=(lambda: self.stop_threads,))
                        self.run_yolo_inf.start()
                elif follow_request.get("following") == "Stop Following":
                    logger.info("Stopping Following")
                    self.command_controller.reset_control_commands()
                    if self.run_yolo_inf is not None and self.run_yolo_inf.is_alive():
                        self.stop_threads = True
                        self.run_yolo_inf.join()  # Wait for the YOLO thread to stop
                if follow_request.get("camera_azimuth") is not None:
                    self.command_controller.current_azimuth = int(follow_request.get("camera_azimuth"))
            except Exception as e:
                logger.error(f"Exception in request_check: {e}")

    def control_logic(self, stop):
        """Processes each frame of YOLO output."""
        for r in self.yolo_inference.results:  # Running the loop for each frame of the stream
            if stop():
                logger.info("YOLO model stopped")
                break
            self.yolo_inference.track_and_save_image(r)
            boxes = r.boxes.cpu().numpy()  # List of bounding boxes in the frame

            self.command_controller.update_control_commands(boxes)

            self.command_controller.publish_command(throttle=self.command_controller.current_throttle, steering=self.command_controller.current_steering, camera_pan=self.command_controller.current_camera_pan)
