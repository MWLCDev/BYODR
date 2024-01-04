from ultralytics import YOLO
import os
import yaml
import logging
from byodr.utils.ipc import JSONZmqClient, JSONServerThread, ReceiverThread
import multiprocessing


quit_event = multiprocessing.Event()

with open("/usr/src/ultralytics/ultralytics/cfg/models/v8/yolov8.yaml") as istream:
    yamldoc = yaml.safe_load(istream)
    yamldoc['nc'] = 1
with open("/usr/src/ultralytics/ultralytics/cfg/models/v8/modified.yaml", "w") as ostream:
    yaml.dump(yamldoc, ostream, default_flow_style=False, sort_keys=False)
    os.rename("/usr/src/ultralytics/ultralytics/cfg/models/v8/modified.yaml","/usr/src/ultralytics/ultralytics/cfg/models/v8/yolov8.yaml")

model = YOLO('../../BYODR/following/50ep320imgsz.pt')
# model = YOLO('yolov8s.pt')

# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

def _on_message(message):
    logger.info(f"Data received from the Teleop service, Listener: {message}.")

#Declaring the inter-service sockets
teleop_receiver = JSONServerThread(url="ipc:///byodr/teleop_to_following.sock", event=quit_event, receive_timeout_ms=50)
teleop_receiver.message_to_send = "Following"
teleop_receiver.add_listener(_on_message)

def detect_objects():
    while True:
        # Setting test data to the inter-service sockets
        # reply_from_teleop = teleop_receiver.call(dict(data = "Following"))
        # logger.info(f"Message received from Teleop: {reply_from_teleop}")

        #results = model.predict(source='rtsp://user1:HaikuPlot876@192.168.2.64:554/Streaming/Channels/102', classes=0, stream=True)
        results = model.predict(source='imgTest/.', classes=0, stream=True)
        print("got results")

        for r in results:
            boxes = r.boxes.cpu().numpy()
            img = r.orig_img

            # xyxy[0, x] for x1, y1, x2, y2
            xyxy = boxes.xyxy
            if xyxy.size > 0:
                x1 = xyxy[0, 0]
                y1 = xyxy[0, 1]
                x2 = xyxy[0, 2]
                y2 = xyxy[0, 3]
                # id = boxes.id
                # print(id)
                # orig_img.shape[0]=height
                # [1]=width
                # [2]=depth
                xCen = int((x1 + x2) / 2)  # only need xcen for navigation
                yBot = int(y2 - y1)  # for distance measurement
                leftE = int(110 / 320 * img.shape[1])
                rightE = int(210 / 320 * img.shape[1])
                topE = int(60 / 240 * img.shape[0])
                botE = int(180 / 240 * img.shape[0])
                # __________left/right speeds
                if xCen <= leftE:
                    # linear
                    v = (-1 / leftE) * xCen + 1  # r wheel = v, l wheel = -v

                    # exponential
                    # a = 1
                    # b = 0.1**(1/130)
                    # v = a*b**float(xCen)

                    tur = 2  # 2 = left, 1 = right, 0 = none
                elif xCen >= rightE:
                    # linear
                    v = 1 / leftE * xCen - rightE / leftE  # r wheel = -v, l wheel = v

                    # exponential
                    # a = 1e6**(12/13)/1e8
                    # b = 10**(1/130)
                    # v = a*b**float(xCen)

                    tur = 1
                else:
                    v = 0
                    tur = 0

                # ___________forward/backward speeds
                if yBot <= topE:
                    # linear
                    d = (-1 / topE) * yBot + 1

                    # exponential
                    # a = 1
                    # b = 0.1**(1/130)
                    # v = a*b**float(xCen)

                    dir = 2  # 2 = forward, 1 = backward, 0 = none
                elif yBot >= botE:
                    # linear
                    d = (-1 / topE) * yBot + 3

                    # exponential
                    # a = 1e6**(12/13)/1e8
                    # b = 10**(1/130)
                    # v = a*b**float(xCen)

                    dir = 1
                else:
                    d = 0
                    dir = 0

                # ______wheel speeds
                if [tur, dir] == [1, 0]:
                    mov = "right in place"
                    vl = v
                    vr = -v
                elif [tur, dir] == [2, 0]:
                    mov = "left in place"
                    vl = -v
                    vr = v
                elif [tur, dir] == [0, 1]:
                    mov = "backward straight"
                    vl = d
                    vr = d
                elif [tur, dir] == [1, 1]:
                    mov = "backward right"
                    vl = -abs(v + d)
                    vr = -abs(-v + d)
                elif [tur, dir] == [2, 1]:
                    mov = "backward left"
                    vl = -abs(-v + d)
                    vr = -abs(v + d)
                elif [tur, dir] == [0, 2]:
                    mov = "forward straight"
                    vl = d
                    vr = d
                elif [tur, dir] == [1, 2]:
                    mov = "forward right"
                    vl = abs(v + d)
                    vr = abs(-v + d)
                elif [tur, dir] == [2, 2]:
                    mov = "forward left"
                    vl = abs(-v + d)
                    vr = abs(v + d)
                else:
                    mov = "stop"
                    vl = 0
                    vr = 0

                print("Left wheel speed = ", vl)
                print("Right wheel speed = ", vr)
                print("Movement direction:", mov)

def main():
    while True:
        logger.info(f"Following working")

if __name__ == "__main__":
    main()
    teleop_receiver.start()
    # detect_objects()