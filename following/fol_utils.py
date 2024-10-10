import logging
import multiprocessing
import os
import threading
import time

import cv2
from byodr.utils.ipc import JSONPublisher
from byodr.utils.option import parse_option
from ultralytics import YOLO

logger = logging.getLogger(__name__)
quit_event = multiprocessing.Event()


class YoloInference:
    """Handles everything related to YOLO inference and obtaining detection results."""

    def __init__(self, model_path, user_config_args):
        self.user_config_args = user_config_args
        self.model_path = model_path
        self.model = YOLO(model_path, task="detect")
        self.image_save_path = "/byodr/yolo_person"
        self.image_counter = 0
        self.results = None
        os.makedirs(self.image_save_path, exist_ok=True)

    def run(self):
        stream_uri = self.get_stream_uri()
        # The persist=True argument tells the tracker that the current image or frame is the next in a sequence and to expect tracks from the previous image in the current image.
        # Streaming mode is beneficial for processing videos or live streams as it creates a generator of results instead of loading all frames into memory.
        # image size is a tuple of (h, w)
        self.results = self.model.track(source=stream_uri, classes=0, stream=True, conf=0.35, persist=True, verbose=False, imgsz=(256, 320), tracker="botsort.yaml")
        logger.info(f"{self.model_path} model is loaded")

    def get_stream_uri(self):
        bottom_camera_uri = parse_option("camera.front.camera.ip", str, "192.168.1.64", [], **self.user_config_args)
        return f"rtsp://user1:HaikuPlot876@{bottom_camera_uri}:554/Streaming/Channels/103"

    def draw_boxes(self, img, results, followed_person_id=None, width=None, height=None):
        """Draw boxes on detected objects (persons) in the returned tensor"""
        for r in results:
            boxes = r.boxes

            for box in boxes:
                # normalized bounding box
                x1n, y1n, x2n, y2n = box.xyxyn[0]
                # scale to image size
                x1, y1, x2, y2 = int(x1n * width), int(y1n * height), int(x2n * width), int(y2n * height)

                # text and background
                label = None
                person_id = int(box.id[0]) if box.id is not None and len(box.id) > 0 and box.id[0] is not None else -1  # Ensure person_id is an int

                if person_id == followed_person_id:
                    label = "Followed"
                else:
                    label = "Not Followed"

                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 1
                thickness = 2
                text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                text_x, text_y = x1, y1
                text_w, text_h = text_size[0], text_size[1]

                # background rectangle for text
                cv2.rectangle(img, (text_x, text_y - text_h), (text_x + text_w, text_y), (182, 77, 180), -1)  # The chosen colour in Figma

                # text on the background
                cv2.putText(img, label, (text_x, text_y - 2), font, font_scale, (255, 255, 255), thickness)

                # put bounding box in the image
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 2)

    def track_and_save_image(self, result, followed_person_id):
        """Tracks objects in video stream and saves the latest image with annotations."""
        img = result.orig_img  # get the original image
        img_height, img_width = result.orig_shape
        img = cv2.resize(img, (img_width // 2, img_height // 2))  # Resize the image to decrease the bandwidth on mobile controller
        self.draw_boxes(img, [result], followed_person_id, width=(img_width // 2), height=(img_height // 2))  # pass the followed person ID and new dimensions
        filename = os.path.join(self.image_save_path, f"image_{self.image_counter}.jpg")
        cv2.imwrite(filename, img)
        self.image_counter += 1

        # Manage saved images to keep only the latest 10
        all_images = sorted(os.listdir(self.image_save_path), key=lambda x: os.path.getctime(os.path.join(self.image_save_path, x)))
        if len(all_images) > 10:
            oldest_image = all_images[0]
            os.remove(os.path.join(self.image_save_path, oldest_image))

    def reset_tracking_session(self):
        """Reset the image counter and clear all images in the directory."""
        self.image_counter = 0
        for existing_file in os.listdir(self.image_save_path):
            os.remove(os.path.join(self.image_save_path, existing_file))


class CommandController:
    """Handles command calculations and publishes them."""

    def __init__(self, user_config_args):
        self.user_config_args = user_config_args
        self.current_throttle = 0
        self.current_steering = 0
        self.current_azimuth = 0
        self.person_height = 0
        self.followed_person_id = None
        self.publisher = JSONPublisher(url="ipc:///byodr/following.sock", topic="aav/following/controls")
        self.calibration_flag = False
        self.get_fol_configs()

    def get_fol_configs(self):
        self.left_red_zone = parse_option("following.left_red_zone", float, 0.45, [], **self.user_config_args)  # In percentage
        self.right_red_zone = parse_option("following.right_red_zone", float, 0.55, [], **self.user_config_args)  # In percentage
        self.unsafe_height = parse_option("following.unsafe_height", float, 0.65, [], **self.user_config_args)  # In percentage
        self.steering_adjustment_factor = parse_option("following.steering_adjustment_factor", int, 3, [], **self.user_config_args)

        self.original_left_red_zone = self.left_red_zone
        self.original_right_red_zone = self.right_red_zone

    def update_control_commands(self, persons):
        """Updates steering, and throttle based on the operator's position on the screen."""
        lowest_id = float("inf")
        person_to_follow = {}

        try:
            # Iterate through each person detected
            for person in persons:
                try:
                    self.person_height = person.xywhn[0][3]
                    # Check if person is too close to the camera
                    if self.person_height >= self.unsafe_height:
                        self.current_throttle = 0
                        self.current_steering = 0
                        return  # Exit the loop early
                    # Skip the person if there is no ID assigned
                    if person.id is None or len(person.id) == 0 or person.id[0] is None:
                        continue

                    person_id = int(person.id[0])
                    # print(person)
                    if person_id < lowest_id:
                        lowest_id = person_id
                        person_to_follow = {"id": person_id, "x_center_percentage": person.xywhn[0][0]}
                except TypeError as e:
                    logger.error(f"Error processing person: {person} with error {e}")

            # If no person was too close, proceed with updating the commands
            if person_to_follow:
                x_center_percentage = person_to_follow["x_center_percentage"]
                self.followed_person_id = int(person_to_follow["id"])
                self.current_throttle = self.calculate_throttle()
                self.current_steering = self.calculate_steering(x_center_percentage)

        except Exception as e:
            logger.error(f"Exception updating control commands: {e}, with person_to_follow: {person_to_follow}")

    def calculate_throttle(self):
        return max(0.2, min(1, ((-(0.01) * self.person_height) + 3.6)))  # 0.2 at 340p height; 1 at 260p height

    def calculate_steering(self, x_center_percentage):
        try:
            if x_center_percentage < self.left_red_zone:
                return -1 + (x_center_percentage / self.left_red_zone)
            elif x_center_percentage > self.right_red_zone:
                return (x_center_percentage - self.right_red_zone) / (1 - self.right_red_zone)
            else:
                return 0
        except Exception as e:
            logger.error(f"Error calculating steering: {e}")
            return 0  # Return neutral steering on error

    def publish_command(self, throttle=0, steering=0, source="Following"):
        """Publishes the control commands to Teleop."""
        try:
            throttle = round(throttle, 3)
            steering = round(steering, 3)

            cmd = {"throttle": throttle, "steering": steering, "source": source}

            self.publisher.publish(cmd)
            # if source == "followingActive" and (cmd["throttle"] != 0 or cmd["steering"] != 0):
            #     print(f'Control commands: T:{cmd["throttle"]}, S:{cmd["steering"]}')
            # logger.info(cmd)
        except Exception as e:
            logger.warning(f"Error while sending teleop command {e}")

    def reset_control_commands(self):
        self.current_throttle = 0
        self.current_steering = 0
        self.publish_command(self.current_throttle, self.current_steering)


class FollowingController:
    """Coordinates between `YoloInference` and `CommandController`."""

    def __init__(self, model_path, user_config_args, event, hz):
        self.yolo_inference = YoloInference(model_path, user_config_args)
        self.command_controller = CommandController(user_config_args)
        self.stop_yolo = threading.Event()
        self.quit_event = event
        self.hz = hz
        self.run_yolo_inf = None
        self.stop_threads = False
        self.fol_state = "loading"

    def initialize_following(self):
        """Initial delay and command to indicate loading state."""
        # As the connection is PUB(FOL)-SUB(TEL), there's no built-in mechanism to ensure that subscriber is ready to receive messages before the publisher starts sending them
        time.sleep(2)
        self.command_controller.publish_command(source="followingLoading")
        self.yolo_inference.run()
        self.fol_state = "inactive"

    def request_check(self):
        """Checks for commands from TEL socket.
        Broadcast the current state of FOL"""
        try:
            teleop_request = self.teleop_chatter()
            if teleop_request is not None:
                if teleop_request.get("following") == "start_following":
                    self.fol_state = "followingActive"
                elif teleop_request.get("following") == "stop_following":
                    self._stop_following()
                elif teleop_request.get("following") == "show_image":
                    self.fol_state = "followingImage"
                    self._start_following()
                elif teleop_request.get("following") == "inactive":
                    self.fol_state = "followingInactive"
                    self._stop_following()
            self._publish_current_state()
        except Exception as e:
            logger.error(f"Exception in request_check: {e}")
            quit_event.set()

    def _start_following(self):
        """Start the following process."""
        if self.run_yolo_inf is None or not self.run_yolo_inf.is_alive():
            self.fol_state = "followingImage"
            self.command_controller.publish_command(
                self.command_controller.current_throttle,
                self.command_controller.current_steering,
                source="followingImage",
            )
            self.yolo_inference.reset_tracking_session()
            self.stop_threads = False
            self.run_yolo_inf = threading.Thread(target=self._control_logic, args=(lambda: self.stop_threads,))
            self.run_yolo_inf.start()

    def _stop_following(self):
        """Stop the following process."""
        self.command_controller.reset_control_commands()
        if self.run_yolo_inf is not None and self.run_yolo_inf.is_alive():
            self.fol_state = "loading"
            self.command_controller.publish_command(source="followingLoading")
            self.stop_threads = True
            self.run_yolo_inf.join()

    def _publish_current_state(self):
        """Keeps broadcasting the current state of following ."""
        # In case there isn't a command received from teleop_chatter and it isn't active or loading, it should send followingInactive
        if self.fol_state == "inactive":
            self.command_controller.publish_command(source="followingInactive")
        # The model should be saving the images only, but not sending commands
        if self.fol_state == "followingImage":
            self.command_controller.publish_command(source="followingImage")
        elif self.fol_state == "followingActive":
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                source="followingActive",
            )

    def _control_logic(self, stop):
        """Processes each frame of YOLO output with a controlled rate."""
        try:
            # print(self.yolo_inference.results)
            for r in self.yolo_inference.results:
                # in case of raising the flag to stop. Terminate the thread and send that fol is ready for future commands
                if stop():
                    logger.info("YOLO model stopped")
                    self.fol_state = "inactive"
                    self.command_controller.publish_command(source="followingReady")
                    break
                self._update_control_commands(r.boxes.cpu().numpy())
                # logger.info(r.speed["preprocess"]+r.speed["inference"]+r.speed["postprocess"])
                followed_person_id = self.command_controller.followed_person_id
                self.yolo_inference.track_and_save_image(r, followed_person_id)
        except Exception as e:
            logger.error(f"Exception in _control_logic: {e}")
            self.quit_event.set()

    def _update_control_commands(self, boxes):
        """Update control commands based on detected boxes."""
        if len(boxes) == 0:
            self.command_controller.current_throttle = 0
            self.command_controller.current_steering = 0
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                source=self.fol_state,
            )
        elif self.fol_state == "followingImage":
            self.command_controller.current_throttle = 0
            self.command_controller.current_steering = 0
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                source="followingImage",
            )
        elif self.fol_state == "followingInactive":
            self.command_controller.current_throttle = 0
            self.command_controller.current_steering = 0
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                source="followingInactive",
            )
        elif self.fol_state == "followingActive":
            self.command_controller.update_control_commands(boxes)
            self.command_controller.publish_command(
                throttle=self.command_controller.current_throttle,
                steering=self.command_controller.current_steering,
                source="followingActive",
            )
