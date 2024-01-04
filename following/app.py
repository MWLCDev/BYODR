import os
#import yaml
import json
import time

import logging
from byodr.utils import timestamp
from byodr.utils.ipc import JSONPublisher, json_collector
import multiprocessing


quit_event = multiprocessing.Event()

# Declaring the logger
logging.basicConfig(format='%(levelname)s: %(asctime)s %(filename)s %(funcName)s %(message)s', datefmt='%Y%m%d:%H:%M:%S %p %Z')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

teleop = json_collector(url="ipc:///byodr/startfollow.sock", topic=b"aav/startfollow/input", event=quit_event)
#teleop = json_collector(url="ipc:///byodr/teleop.sock", topic=b"aav/teleop/input", event=quit_event, hwm=20, pop=True)
request = teleop.get()
teleop.start()

def main():
    logger.info(f"Following working")
    following_publisher = JSONPublisher(
        url="ipc:///byodr/following.sock", topic="aav/following/controls"
    )


    # {'throttle': 0.901, 'steering': 0.094, 'button_b': 1, 'time': 1704365594303983, 'navigator': {'route': None}}
    # {'throttle': 0.8, 'steering': 0, 'button_b': 1, 'time': 1704366201390230, 'navigator': {'route': None}}

    while True:
        cmd = {
        'throttle':0.8,
        'steering':0,
        'button_b':1,
        'time':timestamp(),
        'navigator': {'route': None}
    }


        # logger.info(f"Sending command to teleop: {cmd}")
        following_publisher.publish(cmd)
        # request = teleop.get()
        # logger.info(f"Message from Teleop: {request}")

if __name__ == "__main__":
    main()
    # detect_objects()