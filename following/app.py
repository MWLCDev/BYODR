import os
import glob
import configparser

import logging
import multiprocessing

# yolov8 library
from ultralytics import YOLO

from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher, json_collector
from byodr.utils.option import parse_option

quit_event = multiprocessing.Event()


# Choosing the trained model
model = YOLO('customDefNano.pt')
# model = YOLO('yolov8n.pt')

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
logger.info(f"Initializing the Following service")

# Sending a subscriptable object to teleop
def pub_init():
    cmd = {
        'throttle': 0,
        'steering': 0,
        'button_b': 0,
        'time': timestamp(),
        'navigator': {'route': None}
    }
    # Publishing the command to Teleop
    logger.info(f"Sending command to teleop: {cmd}")
    following_publisher.publish(cmd)

def _config():
    parser = configparser.ConfigParser()
    [parser.read(_f) for _f in glob.glob(os.path.join("/config", "*.ini"))]
    return dict(parser.items("vehicle")) if parser.has_section("vehicle") else {}

def main():
        global clear_path
        clear_path = 4
        global no_human_counter
        throttle = 0
        steering = 0
        # Edges on the screen beyond which robot should start moving to keep distance
        left_edge = 310   # Left edge, away from the left end of the screen
        right_edge = 330  # Right edge, away from the right end if image width = 640p
        bottom_edge = 220    # Bot edge, away from the top end if image height = 480p
        safe_edge = 260
    # Default control commands
        request = teleop.get()
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
            logger.info("Failed to receive a 'Start' request from Teleop")
            cmd = {
                'throttle': 0,
                'steering': 0,
                'button_b': 0,
                'time': timestamp(),
                'navigator': {'route': None}
            }
            # Publishing the command to Teleop
            following_publisher.publish(cmd)
            return
        # Initializing the recognition model
        # Use model.predict for simple prediction, model.track for tracking (when multiple people are present)
        # 'for' loop used when yolov8 model parameter stream = True
        for r in results:
            clear_path += 1
            request = teleop.get()
            if request is not None:
                logger.info(f"Received request from Teleop:{request['following']}")
            try:
                if request is not None and request['following'] == "Stop Following":
                    return
            except:
                logger.info("Failed to receive a 'Stop' request from Teleop")
            boxes = r.boxes.cpu().numpy()       # Bounding boxes around the recognized objects
            # img = r.orig_img                    # Original image (without bboxes, reshaping)
            xyxy = boxes.xyxy                   # X and Y coordinates of the top left and bottom right corners of bboxes

            if xyxy.size > 0:                   # If anything detected

                no_human_counter = 0

                # Getting each coordinate of the bbox corners
                for box in boxes:
                    x1 = box.xyxy[0,0]
                    y1 = box.xyxy[0,1]
                    x2 = box.xyxy[0,2]
                    y2 = box.xyxy[0,3]
                    if int(y2) >= safe_edge or int(y2 - y1) >= safe_edge:
                        clear_path = 0
                    try:
                        if box.id == boxes.id[0]:
                            print("confs: ", boxes.conf, "IDs: ", boxes.id)
                            print("following conf: ", box.conf, "with ID: ", box.id)
                            # Calculating coordinates on the screen
                            box_center = int((x1 + x2) / 2)   # Center of the bbox
                            box_bottom = int(y2)  # Bottom edge of the bbox
                            height = int(y2 - y1) # Height of the bbox
                            logger.info(f"Bottom edge: {box_bottom}, Center: {box_center}, Height: {height}")
                    except:
                        if (box.xyxy==boxes.xyxy[0]).all:
                            print("confs: ", boxes.conf)
                            print("following conf: ", box.conf)
                            # Calculating coordinates on the screen
                            box_center = int((x1 + x2) / 2)   # Center of the bbox
                            box_bottom = int(y2)  # Bottom edge of the bbox
                            height = int(y2 - y1) # Height of the bbox
                            logger.info(f"Bottom edge: {box_bottom}, Center: {box_center}, Height: {height}")
                # throttle: 0 to 1
                # steering: -1 to 1, - left, + right
                # Bbox center crossed the top edge
                if height <= bottom_edge or box_bottom <= bottom_edge:
                    # Linear increase of throttle
                    throttle = (-(0.01) * height) + 2.4 # 0.2 minimum at 220 heigh, 1 max at 140p height
                    if throttle > 1:
                        throttle = 1
                else:
                    throttle = 0

                # Bbox center crossed the left edge
                if box_center <= left_edge:
                    # Linear increase of steering
                    steering = ((0.00238095) * box_center - (0.738095))  # 0 minimum at 310p edge, 0.5 max at 100p 
                    if steering < -0.5:
                        steering = -0.5
                    steering = steering*(1.15-0.75*throttle)    #max steering 0.2-0.5 depending on throttle value
                    if throttle == 0:
                        throttle = abs(steering)/1.15
                        steering = -1
                # Bbox center crossed the right edge
                elif box_center >= right_edge:
                    # Linear increase of steering
                    steering = ((0.00238095) * box_center - (0.785714)) # 0 minimum at 330p edge, 0.5 max at 540p 
                    if steering > 0.5:
                        steering = 0.5
                    steering = steering*(1.15-0.75*throttle)    #max steering 0.2-0.5
                    if throttle == 0:
                        throttle = steering/1.15
                        steering = 1
                else:
                    steering = 0

            else:

                no_human_counter += 1

                logger.info(f"No human detected for {no_human_counter} frames")

                if no_human_counter >= 3:
                    throttle = 0
                    steering = 0

            
            if clear_path <= 3:
                throttle = 0
                logger.info(f"Detected person too close. {clear_path} / 3 frames with clear path")

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

    logger.info(f"Loading YOLOv8 model")

    errors = []
    _config = _config()
    stream_uri = parse_option('ras.master.uri', str, '192.168.1.32', errors, **_config)
    stream_uri = f"rtsp://user1:HaikuPlot876@{stream_uri[:-2]}64:554/Streaming/Channels/103"
    results = model.track(source=stream_uri, classes=0, stream=True, conf=0.4, persist=True)
    logger.info(f"Following ready")
    # results = model.track(source='testImg/.', classes=0, stream=True, conf=0.3, max_det=3, persist=True)

    while True:
        main()
