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
        self.model = YOLO(model_path, task="detect")
        self.image_save_path = "/byodr/yolo_person"
        self.image_counter = 0
        self.results = None

        os.makedirs(self.image_save_path, exist_ok=True)

    def run(self):
        stream_uri = self.get_stream_uri()
        # track() method ensures that the tracker persists across frame
        self.results = self.model.track(source=stream_uri, classes=0, stream=True, conf=0.35, persist=True, verbose=False, tracker="botsort.yaml")
        logger.info("Yolo model is loaded")

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
        self.publisher = JSONPublisher(url="ipc:///byodr/following.sock", topic="aav/following/controls")
        self.calibration_flag = False  # New flag for calibration process

        self.get_fol_configs()

    def get_fol_configs(self):
        self.pan_movement_offset = parse_option("camera.pan_movement_offset", int, 50, [], **self.user_config_args)
        self.left_red_zone = parse_option("following.left_red_zone", float, 0.45, [], **self.user_config_args)
        self.right_red_zone = parse_option("following.right_red_zone", float, 0.55, [], **self.user_config_args)
        self.max_camera_pan_safe_zone = parse_option("following.max_camera_pan_safe_zone", float, 3450, [], **self.user_config_args)  # max is 3600
        self.min_camera_pan_safe_zone = parse_option("following.min_camera_pan_safe_zone", float, 150, [], **self.user_config_args)
        self.start_height = parse_option("following.start_height", int, 340, [], **self.user_config_args)

        self.original_left_red_zone = self.left_red_zone
        self.original_right_red_zone = self.right_red_zone

    def update_control_commands(self, persons):
        """Updates camera pan, steering, and throttle based on the operator's position on the screen."""
        for person in persons:
            try:
                self.person_height = person.xywh[0][3]
                # The horizontal position of the (detected person's bounding box center) within the frame
                x_center_percentage = person.xywhn[0][0]

                self.current_camera_pan = int(self.calculate_camera_pan(x_center_percentage))
                self.current_steering = self.calculate_steering(x_center_percentage)
                self.current_throttle = self.calculate_throttle()

                # Check if calibration is needed
                self.check_calibration_needed(x_center_percentage)

                if self.calibration_flag:
                    self.perform_calibration()

                break  # Only process the first detected person
            except Exception as e:
                logger.warning(f"Exception updating control commands: {e}")

    def check_calibration_needed(self, x_center_percentage):
        """Check if calibration is needed and raise the flag if necessary."""
        # print(self.left_red_zone, x_center_percentage, self.right_red_zone)
        # print(self.min_camera_pan_safe_zone, self.current_azimuth, self.max_camera_pan_safe_zone)
        if (self.left_red_zone <= x_center_percentage <= self.right_red_zone) and (self.min_camera_pan_safe_zone <= self.current_azimuth <= self.max_camera_pan_safe_zone):
            self.calibration_flag = True
            self.left_red_zone /= 2
            self.right_red_zone /= 2
        else:
            self.calibration_flag = False
            self.left_red_zone = self.original_left_red_zone
            self.right_red_zone = self.original_right_red_zone

    def perform_calibration(self):
        """Perform the calibration process to align the vehicle with the camera direction."""
        if self.current_azimuth < 1800:
            self.current_steering = (self.current_azimuth - 1800) / 1800 / 3
        else:
            self.current_steering = (1800 - self.current_azimuth) / 1800 / 3

        self.current_steering = max(-1, min(1, self.current_steering))
        self.current_camera_pan = -self.current_steering * self.pan_movement_offset
        logger.info(f"S:{self.current_steering} C_P:{self.current_camera_pan}")

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
                    return self.pan_movement_offset // 4
                else:
                    return self.pan_movement_offset // 4
        return 0

    def calculate_pan_adjustment(self, x_center_percentage):
        """Sends a normalized value for camera pan, based on how deep is OP in the red zone"""
        if x_center_percentage < self.left_red_zone:
            return self.pan_movement_offset * ((self.left_red_zone - x_center_percentage) / self.left_red_zone)
        elif x_center_percentage > self.right_red_zone:
            return self.pan_movement_offset * ((x_center_percentage - self.right_red_zone) / (1 - self.right_red_zone))
        return 0

    def calculate_steering(self, x_center_percentage):
        if x_center_percentage < self.left_red_zone:
            return -1 + (x_center_percentage / self.left_red_zone)
        elif x_center_percentage > self.right_red_zone:
            return (x_center_percentage - self.right_red_zone) / (1 - self.right_red_zone)
        else:
            return 0

    def publish_command(self, throttle=0, steering=0, camera_pan=0, source="Following"):
        """Publishes the control commands to Teleop."""
        try:
            throttle = round(throttle, 3)
            steering = round(steering, 3)

            cmd = {"throttle": throttle, "steering": steering, "button_b": 1, "source": source}

            if camera_pan is not None:
                # Make sure to define the preset for the camera
                if camera_pan == "go_preset_1":
                    cmd["camera_pan"] = camera_pan
                else:
                    cmd["camera_pan"] = int(camera_pan)
                self.publisher.publish(cmd)
            if source not in ["followingInactive", "followingLoading"]:
                logger.info(f'Control commands: T:{cmd["throttle"]}, S:{cmd["steering"]}, C_P:{cmd.get("camera_pan", "N/A")}')
        except Exception as e:
            logger.warning(f"Error while sending teleop command {e}")

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
        self.run_yolo_inf = None
        self.stop_threads = False
        self.stop_yolo = threading.Event()
        self.fol_state = "loading"

    def initialize_following(self):
        """Initial delay and command to indicate loading state."""
        # As the connection is PUB(FOL)-SUB(TEL), there's no built-in mechanism to ensure that subscriber is ready to receive messages before the publisher starts sending them
        time.sleep(2)
        self.command_controller.publish_command(source="followingLoading")
        self.yolo_inference.run()
        self.fol_state = "inactive"

    def request_check(self):
        """Fetches and processes the request from Teleop."""
        try:
            teleop_request = self.teleop_chatter()
            if teleop_request is not None:
                if teleop_request.get("following") == "start_following":
                    self._start_following()
                elif teleop_request.get("following") == "stop_following":
                    self._stop_following()
                elif teleop_request.get("camera_azimuth") is not None:
                    self.command_controller.current_azimuth = int(teleop_request.get("camera_azimuth"))
                    # print(self.command_controller.current_azimuth)
            self._publish_current_state()
        except Exception as e:
            logger.error(f"Exception in request_check: {e}")

    def _start_following(self):
        """Start the following process."""
        if self.run_yolo_inf is None or not self.run_yolo_inf.is_alive():
            self.fol_state = "active"
            self.command_controller.publish_command(self.command_controller.current_throttle, self.command_controller.current_steering, camera_pan="go_preset_1")
            self.yolo_inference.reset_tracking_session()
            self.stop_threads = False
            self.run_yolo_inf = threading.Thread(target=self._control_logic, args=(lambda: self.stop_threads,))
            self.run_yolo_inf.start()

    def _stop_following(self):
        """Stop the following process."""
        logger.info("Stopping Following")
        self.command_controller.reset_control_commands()
        if self.run_yolo_inf is not None and self.run_yolo_inf.is_alive():
            self.fol_state = "loading"
            self.command_controller.publish_command(source="followingLoading")
            self.stop_threads = True
            self.run_yolo_inf.join()

    def _publish_current_state(self):
        """Publish the current state of following."""
        # In case there isn't a command received from teleop_chatter and it isn't active or loading, it should send followingInactive
        if self.fol_state == "inactive":
            self.command_controller.publish_command(source="followingInactive")
        # As the model sends when it has new data, there sin't a way for the ui to keep showing the stream box. This condition here is to cover for these gaps
        elif self.fol_state == "active":
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                camera_pan=self.command_controller.current_camera_pan,
                source="followingActive",
            )

    def _control_logic(self, stop):
        """Processes each frame of YOLO output."""
        for r in self.yolo_inference.results:
            if stop():
                logger.info("YOLO model stopped")
                self.fol_state = "inactive"
                self.command_controller.publish_command(source="followingReady")
                break
            self.yolo_inference.track_and_save_image(r)
            self._update_control_commands(r.boxes.cpu().numpy())

    def _update_control_commands(self, boxes):
        """Update control commands based on detected boxes."""
        if len(boxes) == 0:
            self.command_controller.current_throttle = 0
            self.command_controller.current_steering = 0
            self.command_controller.current_camera_pan = 0
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                camera_pan=self.command_controller.current_camera_pan,
                source="followingActive",
            )
        else:
            self.command_controller.update_control_commands(boxes)
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                camera_pan=self.command_controller.current_camera_pan,
                source="followingActive",
            )
