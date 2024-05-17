import configparser
import glob
import logging
import multiprocessing
import os

import cv2
from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.option import parse_option
from ultralytics import YOLO

LEFT_EDGE = 310
RIGHT_EDGE = 330
BOTTOM_EDGE = 450
SAFE_EDGE = 475
MAX_HUMAN_ABSENCE_FRAMES = 3
MIN_CLEAR_PATH_FRAMES = 3
SMOOTH_CONTROL_STEP = 0.1  # 10%


class FollowingController:
    def __init__(self, model_path, config_path="/config"):
        self.quit_event = multiprocessing.Event()
        self.model = YOLO(model_path)
        self.no_human_counter = 0
        self.clear_path = 4
        self.logger = self.setup_logger()
        self.config = self.load_config(config_path)
        self.teleop = self.setup_teleop_receiver()
        self.publisher = self.setup_publisher()
        self.current_throttle = 0
        self.current_steering = 0
        self.image_counter = 0
        self.image_save_path = "/byodr/yolo_person"
        os.makedirs(self.image_save_path, exist_ok=True)

    def reset_tracking_session(self):
        """Reset the image counter and clear all images in the directory."""
        self.image_counter = 0
        for existing_file in os.listdir(self.image_save_path):
            os.remove(os.path.join(self.image_save_path, existing_file))
        self.logger.info("Tracking session reset: Image counter zeroed and folder cleared.")

    def setup_logger(self):
        logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        return logger

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

    def load_config(self, path):
        parser = configparser.ConfigParser()
        [parser.read(f) for f in glob.glob(os.path.join(path, "*.ini"))]
        return dict(parser.items("vehicle")) if parser.has_section("vehicle") else {}

    def setup_teleop_receiver(self):
        teleop = json_collector(url="ipc:///byodr/teleop_c.sock", topic=b"aav/teleop/chatter", pop=True, event=self.quit_event, hwm=1)
        teleop.start()
        return teleop

    def setup_publisher(self):
        return JSONPublisher(url="ipc:///byodr/following.sock", topic="aav/following/controls")

    def publish_command(self, throttle, steering, button_b=1, camera_pan=None):
        cmd = {"throttle": throttle, "steering": steering, "button_b": button_b, "time": timestamp(), "navigator": {"route": None}}
        if camera_pan is not None:
            cmd["camera_pan"] = camera_pan
        self.publisher.publish(cmd)
        self.logger.info(f"Sending command to teleop: Throttle {cmd['throttle']}, Steering {cmd['steering']}, Camera Pan {cmd.get('camera_pan', 'N/A')}")

    def stop_robot(self):
        self.current_throttle = 0
        self.current_steering = 0
        self.publish_command(0, 0)

    def analyze_frame(self, boxes):
        clear_path = self.clear_path
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0, :]
            if y2 >= SAFE_EDGE or (y2 - y1) >= SAFE_EDGE:
                return 0
        if self.no_human_counter >= MAX_HUMAN_ABSENCE_FRAMES:
            return 0
        clear_path += 1
        return clear_path

    def control_logic(self, results):
        for r in results:
            boxes = r.boxes.cpu().numpy()
            self.clear_path = self.analyze_frame(boxes)
            throttle, steering = self.decide_control(boxes)
            request = self.teleop.get()
            self.track_and_save_image(r)
            try:
                if request["following"] == "Stop Following":
                    self.logger.info("Stopping Following")
                    self.stop_robot()
                    return
            except:
                pass
            self.publish_command(throttle, steering)

    def smooth_controls(self, target_throttle, target_steering):
        if self.current_throttle <= target_throttle * (1 - SMOOTH_CONTROL_STEP):
            self.current_throttle += SMOOTH_CONTROL_STEP * target_throttle
        else:
            self.current_throttle = target_throttle
        if self.current_steering <= target_steering * (1 - SMOOTH_CONTROL_STEP):
            self.current_steering += SMOOTH_CONTROL_STEP * target_steering
        else:
            self.current_steering = target_steering

    def decide_control(self, boxes):
        if not boxes.xyxy.size:
            self.no_human_counter += 1
            # self.logger.info(f"No person detected for: {self.no_human_counter} frames")
            try:
                return throttle, steering
            except:
                return 0, 0

        throttle, steering = 0, 0
        self.no_human_counter = 0
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0, :]
            box_center = (x1 + x2) / 2
            box_bottom = y2
            box_height = y2 - y1
            # self.logger.info(f"Bottom edge: {int(box_bottom)}, Center: {int(box_center)}, Height: {int(box_height)}")
            if box_bottom <= BOTTOM_EDGE or box_height <= BOTTOM_EDGE:
                throttle = max(0, min(1, ((-(0.008) * box_height) + 3.88)))

            if box_center <= LEFT_EDGE:
                steering = max(-1, min(1, (0.00238095 * box_center - 0.738095)))
                steering = steering * (1.15 - 0.75 * throttle)  # max steering 0.2-0.5 depending on throttle value
                if throttle == 0:
                    throttle = abs(steering) / 1.15
                    steering = -1
            elif box_center >= RIGHT_EDGE:
                steering = max(-1, min(1, (0.00238095 * box_center - 0.785714)))
                steering = steering * (1.15 - 0.75 * throttle)  # max steering 0.2-0.5 depending on throttle value
                if throttle == 0:
                    throttle = steering / 1.15
                    steering = 1
        if self.clear_path <= MIN_CLEAR_PATH_FRAMES:
            # self.logger.info(f"Path obstructed. {self.clear_path} / 3 frames with clear path")
            throttle = 0
        throttle = 1
        self.smooth_controls(throttle, steering)
        return self.current_throttle, self.current_steering

    def run(self):
        self.stop_robot()  # Initialize with safe values
        self.logger.info("Following ready to start")
        errors = []
        stream_uri = parse_option("ras.master.uri", str, "192.168.1.32", errors, **self.config)
        stream_uri = f"rtsp://user1:HaikuPlot876@{stream_uri[:-2]}65:554/Streaming/Channels/103"
        while True:
            request = self.teleop.get()
            try:
                if request["following"] == "Start Following":
                    self.reset_tracking_session()
                    self.logger.info("Loading Yolov8 model")
                    results = self.model.track(source=stream_uri, classes=0, stream=True, conf=0.4, persist=True, verbose=False)
                    self.control_logic(results)
            except:
                pass


if __name__ == "__main__":
    controller = FollowingController("customDefNano.pt")
    controller.run()
