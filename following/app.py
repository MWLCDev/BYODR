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

# from simple_pid import PID
# pid = PID(0.002, 2.8, 0, setpoint=0)
# pid.output_limits = (-1, 1)

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
model = YOLO('customDefNano.pt')
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
        try:
            if request is None or request['following'] == "Stop Following":
                cmd = {
                    'throttle': 0,
                    'steering': 0,
                    'button_b': 1,
                    'time': timestamp(),
                    'navigator': {'route': None}
                }
                # Publishing the command to Teleop
                following_publisher.publish(cmd)
                return
        except:
            print("can't get message from following")
            cmd = {
                'throttle': 0,
                'steering': 0,
                'button_b': 1,
                'time': timestamp(),
                'navigator': {'route': None}
            }
            # Publishing the command to Teleop
            following_publisher.publish(cmd)
            return
        # Initializing the recognition model
        # Use model.predict for simple prediction, model.track for tracking (when multiple people are present)
        # 'for' loop used when yolov8 model parameter stream = True
        logger.info("got results")

        for r in results:
            # lastThrottle = throttle
            request = teleop.get()
            if request is not None:
                print(request['following'])
            try:
                if request is not None and request['following'] == "Stop Following":
                    return
            except:
                print("can't get message from teleop")
            boxes = r.boxes.cpu().numpy()       # Bounding boxes around the recognized objects
            img = r.orig_img                    # Original image (without bboxes, reshaping)
            xyxy = boxes.xyxy                   # X and Y coordinates of the top left and bottom right corners of bboxes
            # print(img.shape)

            if xyxy.size > 0:                   # If anything detected

                no_human_counter = 0

                # Getting each coordinate of the bbox corners
                if boxes.id is not None and boxes.id.size > 1:
                    for box in boxes:
                        if box.id == boxes.id[0]:
                            x1 = box.xyxy[0,0]
                            y1 = box.xyxy[0,1]
                            x2 = box.xyxy[0,2]
                            y2 = box.xyxy[0,3]
                            print(box.id)
                else:
                    x1 = xyxy[0, 0]
                    y1 = xyxy[0, 1]
                    x2 = xyxy[0, 2]
                    y2 = xyxy[0, 3]
                # Calculating coordinates on the screen
                xCen = int((x1 + x2) / 2)   # Center of the bbox
                yBot = int(y2)  # Bottom edge of the bbox
                height = int(y2 - y1) # Height of the bbox
                logger.info(f"Bottom edge: {yBot}, Center: {xCen}, Height: {height}")

                # Edges on the screen beyond which robot should start moving to keep distance
                leftE = int(310 / 640 * img.shape[1])   # Left edge, away from the left end of the screen
                rightE = int(330 / 640 * img.shape[1])  # Right edge, away from the right end if image width = 640p
                botE = int(300 / 480 * img.shape[0])    # Bot edge, 190p away from the top end if image height = 480p
                # botE = int(180 / 240 * img.shape[0])  # Bot edge, used only if robot can move backwards
                # throttle: 0 to 1
                # steering: -1 to 1, - left, + right
                # Bbox center crossed the top edge
                if height <= botE or yBot <= botE:
                    # Linear increase of throttle
                    # throttle = (-(0.01) * yBot) + 2.2 # 0.2 minimum at 200p edge, max at 120p edge
                    throttle = (-(0.02) * height) + 6.2 # 0.2 minimum at 300p heigh, 1 max at 260p height
                    if throttle > 1:
                        throttle = 1
                else:
                    throttle = 0

                # Bbox center crossed the left edge
                if xCen <= leftE:
                    # steering = -0.4
                    # Linear increase of steering
                    steering = ((0.00238095) * xCen - (0.738095))*(1.2-throttle)  # 0 minimum at 310p edge, 0.5 max at 100p
                    if steering < -0.5:
                        steering = -0.5
                    if throttle == 0:
                        throttle = abs(steering)/1.2
                        steering = -1
                # Bbox center crossed the right edge
                elif xCen >= rightE:
                    # steering = 0.4
                    # Linear increase of steering
                    steering = ((0.00238095) * xCen - (0.785714))*(1.2-throttle) # 0 minimum at 330p edge, 0.5 max at 540p
                    if steering > 0.5:
                        steering = 0.5
                    if throttle == 0:
                        throttle = steering/1.2
                        steering = 1
                else:
                    steering = 0

                # pid.setpoint = throttle
                # throttle = pid(lastThrottle)

                if height >= 340 or yBot >= 340:
                    throttle = 0

            else:

                no_human_counter = no_human_counter + 1

                logger.info(f"No human detected for {no_human_counter} frames")


                if no_human_counter >= 1:
                    print("______________________________________stopped after losing")
                    throttle = 0
                    steering = 0

            # Defining the control command to be sent to Teleop
            cmd = {
                'throttle':throttle,
                'steering':-steering,
                # 'throttle':1,
                # 'steering':0.1,
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
    results = model.track(source='rtsp://user1:HaikuPlot876@192.168.1.64:554/Streaming/Channels/103', classes=0, stream=True, conf=0.3, max_det=3, persist=True)
    # results = model.track(source='imgTest/.', classes=0, stream=True, conf=0.35, max_det=3, persist=True)

    while True:
        main()
