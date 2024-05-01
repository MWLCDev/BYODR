import os
import glob
import configparser
import logging
import multiprocessing
from ultralytics import YOLO
from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.option import parse_option

# Constants
LEFT_EDGE = 310
RIGHT_EDGE = 330
BOTTOM_EDGE = 450
SAFE_EDGE = 475
MAX_HUMAN_ABSENCE_FRAMES = 3
MIN_CLEAR_PATH_FRAMES = 3
SMOOTH_CONTROL_STEP = 0.1 # 10%


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

    def setup_logger(self):
        logging.basicConfig(format="%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s", datefmt="%Y%m%d:%H:%M:%S %p %Z")
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        return logger

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

    def publish_command(self, throttle, steering, button_b=1):
        cmd = {"throttle": throttle, "steering": steering, "button_b": button_b, "time": timestamp(), "navigator": {"route": None}}
        self.publisher.publish(cmd)
        self.logger.info(f"Sending command to teleop: {cmd}")

    def stop_robot(self):
        self.current_throttle = 0
        self.current_steering = 0
        self.publish_command(0, 0)

    def analyze_frame(self, boxes):
        clear_path = self.clear_path
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0,:]
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
            try:
                if request['following'] == "Stop Following":
                    self.logger.info("Stopping Following")
                    self.stop_robot()
                    return
            except:
                pass
            self.publish_command(throttle, steering)

    def smooth_controls(self, target_throttle, target_steering):
        if self.current_throttle <= target_throttle*(1-SMOOTH_CONTROL_STEP):
            self.current_throttle += (SMOOTH_CONTROL_STEP * target_throttle)
        else:
            self.current_throttle = target_throttle
        if self.current_steering <= target_steering*(1-SMOOTH_CONTROL_STEP):
            self.current_steering += (SMOOTH_CONTROL_STEP * target_steering)
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
            x1, y1, x2, y2 = box.xyxy[0,:]
            box_center = (x1 + x2) / 2
            box_bottom = y2
            box_height = y2 - y1
            # self.logger.info(f"Bottom edge: {int(box_bottom)}, Center: {int(box_center)}, Height: {int(box_height)}")
            if box_bottom <= BOTTOM_EDGE or box_height <= BOTTOM_EDGE:
                throttle = max(0, min(1, ((-(0.008) * box_height) + 3.88)))

            if box_center <= LEFT_EDGE:
                steering = max(-1, min(1, (0.00238095 * box_center - 0.738095)))
                steering = steering*(1.15-0.75*throttle)    #max steering 0.2-0.5 depending on throttle value
                if throttle == 0:
                    throttle = abs(steering)/1.15
                    steering = -1
            elif box_center >= RIGHT_EDGE:
                steering = max(-1, min(1, (0.00238095 * box_center - 0.785714)))
                steering = steering*(1.15-0.75*throttle)    #max steering 0.2-0.5 depending on throttle value
                if throttle == 0:
                    throttle = steering/1.15
                    steering = 1
        if self.clear_path <= MIN_CLEAR_PATH_FRAMES:
            # self.logger.info(f"Path obstructed. {self.clear_path} / 3 frames with clear path")
            throttle = 0
        throttle = 1
        self.smooth_controls(throttle, steering)
        return self.current_throttle, self.current_steering

    def run(self):
        self.stop_robot  # Initialize with safe values
        self.logger.info("Following ready to start")
        errors = []
        _config = self.config
        stream_uri = parse_option('ras.master.uri', str, '192.168.1.32', errors, **_config)
        stream_uri = f"rtsp://user1:HaikuPlot876@{stream_uri[:-2]}65:554/Streaming/Channels/103"
        while True:
            request = self.teleop.get()
            try:
                if request['following'] == "Start Following":
                    self.logger.info("Loading Yolov8 model")
                    results = self.model.track(source=stream_uri, classes=0, stream=True, conf=0.4, persist=True, verbose=False)
                    self.control_logic(results)
            except:
                pass
                


if __name__ == "__main__":
    controller = FollowingController("customDefNano.pt")
    controller.run()