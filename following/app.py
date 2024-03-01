# Both libraries to access the yolov8 yaml inside the robot
import os
import yaml

# import json
# import time
import logging
import multiprocessing
# import subprocess
# import cv2

# yolov8 library
from ultralytics import YOLO
# import torch

from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher, json_collector

quit_event = multiprocessing.Event()

# # Accessing the yolov8.yaml inside the robot to remove unnecessary classes
# with open("/workspace/ultralytics/ultralytics/cfg/models/v8/yolov8.yaml") as istream:
#     yamldoc = yaml.safe_load(istream)
#     yamldoc['nc'] = 1
# # Replacing the default yaml with a modified one
# with open("/workspace/ultralytics/ultralytics/cfg/models/v8/modified.yaml", "w") as ostream:
#     yaml.dump(yamldoc, ostream, default_flow_style=False, sort_keys=False)
#     os.rename("/workspace/ultralytics/ultralytics/cfg/models/v8/modified.yaml", "/workspace/ultralytics/ultralytics/cfg/models/v8/yolov8.yaml")

# Choosing the trained model
model = YOLO('50ep320imgsz.pt')
# model = YOLO('yolov8n.pt')
#model.to(device=device)

no_human_counter = 0


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
        
        global no_human_counter
        throttle = 0
        steering = 0
    # Default control commands
        # logger.info(f"Waiting for request")
        request = teleop.get()
        # logger.info(f"Message from teleop chatter: {request}")
        # results = model.predict(source='imgTest/.', classes=0, stream=True)     # imgTest = folder with sample images
        if request is None or request['following'] == "Stop Following":
            cmd = {
                'throttle': 0,
                'steering': 0,
                'button_b': 1,
                'time': timestamp(),
                'navigator': {'route': None}
            }
            # Publishing the command to Teleop
            # logger.info(f"Sending command to teleop: {cmd}")
            following_publisher.publish(cmd)
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
            # print(img.shape)

            if xyxy.size > 0:                   # If anything detected

                no_human_counter = 0

                # Getting each coordinate of the bbox corners
                x1 = xyxy[0, 0]
                y1 = xyxy[0, 1]
                x2 = xyxy[0, 2]
                y2 = xyxy[0, 3]
                # id = boxes.id     # Used when model.track to choose a specific object in view
                if boxes.id is not None and boxes.id.size > 1:
                    for box in boxes:
                        if box.id == 1:
                            x1 = box.xyxy[0,0]
                            y1 = box.xyxy[0,1]
                            x2 = box.xyxy[0,2]
                            y2 = box.xyxy[0,3]
                # Calculating coordinates on the screen
                xCen = int((x1 + x2) / 2)   # Center of the bbox
                yBot = int(y2 - y1)  # Bottom edge of the bbox
                logger.info(f"Bottom edge: {yBot}, Center: {xCen}")

                # Edges on the screen beyond which robot should start moving to keep distance
                leftE = int(240 / 640 * img.shape[1])   # Left edge, 240p away from the left end of the screen
                rightE = int(400 / 640 * img.shape[1])  # Right edge, 240p away from the right end if image width = 640p
                botE = int(200 / 480 * img.shape[0])    # Bot edge, 190p away from the top end if image height = 480p
                # botE = int(180 / 240 * img.shape[0])  # Bot edge, used only if robot can move backwards
                # throttle: 0 to 1
                # steering: -1 to 1, - left, + right
                # Bbox center crossed the top edge
                if yBot <= botE:
                    # throttle = 0.7
                    # Linear increase of throttle
                    throttle = (-(0.01) * yBot) + 2.3 # 0.3 minimum at 200p edge, max at 130p edge

                else:
                    throttle = 0

                # Bbox center crossed the left edge
                if xCen <= leftE:
                    # steering = -0.4
                    # Linear increase of steering
                    steering = (0.0025) * xCen - (0.8)  # 0.2 minimum at 240p edge
                    # Robot needs throttle to turn left/right
                    if throttle < abs(steering):
                        throttle = abs(steering)
                # Bbox center crossed the right edge
                elif xCen >= rightE:
                    # steering = 0.4
                    # Linear increase of steering
                    steering = (0.0025) * xCen - (0.8) # 0.2 minimum at 400p edge
                    # Robot needs throttle to turn left/right
                    if throttle < abs(steering):
                        throttle = abs(steering)
                else:
                    steering = 0

                
                #caveman
                if throttle > 1:
                    throttle = 1
                if steering < -1:
                    steering = -1
                elif steering > 1:
                    steering = 1
                if yBot >= 255:
                    throttle = 0

            else:

                no_human_counter = no_human_counter + 1

                logger.info(f"No human detected for {no_human_counter} frames")



                if no_human_counter == 15:
                    throttle = 0
                    steering = 0

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
    results = model.track(source='rtsp://user1:HaikuPlot876@192.168.1.64:554/Streaming/Channels/103', classes=0, stream=True, conf=0.35, max_det=3)
    # results = model.predict(source='imgTest/.', classes=0, stream=True, conf=0.35, max_det=3)

    while True:
        main()
