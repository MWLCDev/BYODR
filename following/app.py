# Both libraries to access the yolov8 yaml inside the robot
import os
import yaml

# import json
# import time
import logging
import multiprocessing
# import subprocess

# yolov8 library
from ultralytics import YOLO
# import torch

from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher, json_collector

quit_event = multiprocessing.Event()

# Accessing the yolov8.yaml inside the robot to remove unnecessary classes
with open("/usr/src/ultralytics/ultralytics/cfg/models/v8/yolov8.yaml") as istream:
    yamldoc = yaml.safe_load(istream)
    yamldoc['nc'] = 1
# Replacing the default yaml with a modified one
with open("/usr/src/ultralytics/ultralytics/cfg/models/v8/modified.yaml", "w") as ostream:
    yaml.dump(yamldoc, ostream, default_flow_style=False, sort_keys=False)
    os.rename("/usr/src/ultralytics/ultralytics/cfg/models/v8/modified.yaml","/usr/src/ultralytics/ultralytics/cfg/models/v8/yolov8.yaml")

# Choosing the trained model
model = YOLO('50ep320imgsz.pt')
# model = YOLO('yolov8n.pt')
#model.to(device=device)

# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Declaring the socket to receive messages from Teleop
teleop = json_collector(url='ipc:///byodr/teleop_c.sock', topic=b'aav/teleop/chatter', pop=True, event=quit_event, hwm=1,)
teleop.start()

# Declaring the socket to send control commands
following_publisher = JSONPublisher(
    url="ipc:///byodr/following.sock", topic="aav/following/controls"
)
logger.info(f"Following working")

# Sending a subscriptable object to teleop
def pub_init():
    cmd = {
        'throttle': 0,
        'steering': 0,
        'button_b': 1,
        'time': timestamp(),
        'navigator': {'route': None}
    }
    # Publishing the command to Teleop
    logger.info(f"Sending command to teleop: {cmd}")
    following_publisher.publish(cmd)

def main():
        throttle = 0
        steering = 0
    # Default control commands
        # logger.info(f"Waiting for request")
        request = teleop.get()
        # logger.info(f"Message from teleop chatter: {request}")
        # results = model.predict(source='imgTest/.', classes=0, stream=True)     # imgTest = folder with sample images
        if request is None or request['following'] == "Stop Following":
            return
        # Initializing the recognition model
        # Use model.predict for simple prediction, model.track for tracking (when multiple people are present)
        # 'for' loop used when yolov8 model parameter stream = True
        logger.info("got results")
        for r in results:
            request = teleop.get()
            if request is not None:
                print(request['following'])
            if request is not None and request['following'] == "Stop Following":
                return
            boxes = r.boxes.cpu().numpy()       # Bounding boxes around the recognized objects
            img = r.orig_img                    # Original image (without bboxes, reshaping)
            xyxy = boxes.xyxy                   # X and Y coordinates of the top left and bottom right corners of bboxes
            if xyxy.size > 0:   # If anything detected

                # Getting each coordinate of the bbox corners
                x1 = xyxy[0, 0]
                y1 = xyxy[0, 1]
                x2 = xyxy[0, 2]
                y2 = xyxy[0, 3]
                # id = boxes.id     # Used when model.track to choose a specific object in view

                # Calculating coordinates on the screen
                xCen = int((x1 + x2) / 2)   # Center of the bbox
                yBot = int(y2 - y1)  # Bottom edge of the bbox
                # Edges on the screen beyond which robot should start moving to keep distance
                leftE = int(100 / 320 * img.shape[1])   # Left edge, 110p away from the left end if image width = 320p
                rightE = int(220 / 320 * img.shape[1])  # Right edge, 110p away from the right end if image width = 320p
                botE = int(120 / 240 * img.shape[0])     # Bot edge, 120p away from the top end if image height = 240p
                # botE = int(180 / 240 * img.shape[0])  # Bot edge, used only if robot can move backwards
                # throttle: 0 to 1
                # steering: -1 to 1, - left, + right
                # Bbox center crossed the top edge
                if yBot <= botE:
                    # Linear increase of throttle
                    # throttle = -(7/800)*yBot+1.35
                    # throttle = 0.3
                    throttle = -(0.00875) * yBot + 1.35
                else:
                    throttle = 0

                # Bbox center crossed the left edge
                if xCen <= leftE:
                    # Linear increase of steering
                    # steering = -(xCen / leftE - 1)
                    # steering = 0.4
                    steering = (0.00875) * xCen - (1.175)
                    # Robot needs throttle to turn left/right
                    if throttle == 0:
                        throttle = 0.3
                # Bbox center crossed the right edge
                elif xCen >= rightE:
                    # Linear increase of steering
                    # steering = -(xCen / leftE - (rightE / leftE))                  
                    # steering = 0.4
                    steering = (0.00875) * xCen - (1.625)
                    # Robot needs throttle to turn left/right
                    if throttle == 0:
                        throttle = 0.3
                else:
                    steering = 0

            # Lowering the throttle and steering values to compensate for delay (temporary)
            # throttle = throttle * 0.7
            # steering = steering * 0.7

            # Defining the control command to be sent to Teleop
            cmd = {
                'throttle':throttle,
                'steering':steering,
                'button_b':1,
                'time':timestamp(),
                'navigator': {'route': None}
            }
            # Publishing the command to Teleop
            logger.info(f"Sending command to teleop: {cmd}")
            following_publisher.publish(cmd)


if __name__ == "__main__":
    pub_init()

    logger.info(f"Starting following model")
    results = model.predict(source='rtsp://user1:HaikuPlot876@192.168.3.64:554/Streaming/Channels/103', classes=0, stream=True, conf=0.35, max_det=3)
    while True:
        main()
