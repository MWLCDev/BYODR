from __future__ import absolute_import

import collections
import datetime
import json
import logging
import multiprocessing
import os
import sys
import threading
import time

import numpy as np
import zmq

from byodr.utils import timestamp

if sys.version_info > (3,):
    # noinspection PyShadowingBuiltins
    buffer = memoryview


    def receive_string(subscriber):
        return subscriber.recv_string()


    def send_string(sender, val, flags=0):
        return sender.send_string(val, flags)
else:
    def receive_string(subscriber):
        return subscriber.recv()


    def send_string(sender, val, flags=0):
        return sender.send(val, flags)

logger = logging.getLogger(__name__)


# Class that publishes data for potential receivers to get it
class JSONPublisher(object):
    def __init__(self, url, topic='', hwm=1, clean_start=True):
        if clean_start and url.startswith('ipc://') and os.path.exists(url[6:]):
            os.remove(url[6:])
        publisher = zmq.Context().socket(zmq.PUB)
        publisher.set_hwm(hwm)
        publisher.bind(url)
        self._publisher = publisher
        self._topic = topic

    # Function to send data
    def publish(self, data, topic=None):
        _topic = self._topic if topic is None else topic
        if data is not None:
            data = dict((k, v) for k, v in data.items() if v is not None)
            send_string(self._publisher, '{}:{}'.format(_topic, json.dumps(data)), zmq.NOBLOCK)

# Class that publishes image for potential receivers to get it
class ImagePublisher(object):
    def __init__(self, url, topic='', hwm=1, clean_start=True):
        if clean_start and url.startswith('ipc://') and os.path.exists(url[6:]):
            os.remove(url[6:])
        publisher = zmq.Context().socket(zmq.PUB)
        publisher.set_hwm(hwm)
        publisher.bind(url)
        self._publisher = publisher
        self._topic = topic

    # Function to send data
    def publish(self, _img, topic=None):
        _topic = self._topic if topic is None else topic
        self._publisher.send_multipart([_topic,
                                        json.dumps(dict(time=timestamp(), shape=_img.shape)),
                                        np.ascontiguousarray(_img, dtype=np.uint8)],
                                       flags=zmq.NOBLOCK)

# Class that connects to a zmq zerver via url
# Receives the data the server is publishing
class JSONReceiver(object):
    def __init__(self, url, topic=b'', hwm=1, receive_timeout_ms=2, pop=False):
        subscriber = zmq.Context().socket(zmq.SUB)
        subscriber.set_hwm(hwm)
        subscriber.setsockopt(zmq.RCVTIMEO, receive_timeout_ms)
        subscriber.setsockopt(zmq.LINGER, 0)
        subscriber.connect(url)
        subscriber.setsockopt(zmq.SUBSCRIBE, topic)
        self._pop = pop
        self._unpack = hwm == 1
        self._subscriber = subscriber
        self._lock = threading.Lock()
        self._queue = collections.deque(maxlen=hwm)

    # Receives data from the server and stores it in an internal queue
    def consume(self):
        with self._lock:
            try:
                # Does not replace local queue messages when none are available.
                self._queue.appendleft(json.loads(receive_string(self._subscriber).split(':', 1)[1]))
            except zmq.Again:
                pass

    # Get the value that is stored inside the queue. Has the ability to clear the queue after receiving
    def get(self):
        _view = self._queue[0] if (self._queue and self._unpack) else list(self._queue) if self._queue else None
        if self._pop:
            self._queue.clear()
        return _view

    # Returns the stored value in the queue
    def peek(self):
        return self._queue[0] if self._queue else None


class CollectorThread(threading.Thread):
    def __init__(self, receivers, event=None, hz=1000):
        super(CollectorThread, self).__init__()
        _list = (isinstance(receivers, tuple) or isinstance(receivers, list))
        self._receivers = receivers if _list else [receivers]
        self._quit_event = multiprocessing.Event() if event is None else event
        self._sleep = 1. / hz

    def get(self, index=0):
        # Get the latest message without blocking.
        # _receiver.consume() -- blocks; perform at thread.run()
        return self._receivers[index].get()

    def peek(self, index=0):
        return self._receivers[index].peek()

    def quit(self):
        self._quit_event.set()

    def run(self):
        while not self._quit_event.is_set():
            # Empty the receiver queues to not block upstream senders.
            list(map(lambda receiver: receiver.consume(), self._receivers))
            time.sleep(self._sleep)


def json_collector(url, topic, event, receive_timeout_ms=1000, hwm=1, pop=False):
    return CollectorThread(JSONReceiver(url, topic, hwm=hwm, receive_timeout_ms=receive_timeout_ms, pop=pop), event=event)


class ReceiverThread(threading.Thread):
    def __init__(self, url, event=None, topic=b'', hwm=1, receive_timeout_ms=1):
        super(ReceiverThread, self).__init__()
        subscriber = zmq.Context().socket(zmq.SUB)
        subscriber.set_hwm(hwm)
        subscriber.setsockopt(zmq.RCVTIMEO, receive_timeout_ms)
        subscriber.setsockopt(zmq.LINGER, 0)
        subscriber.connect(url)
        subscriber.setsockopt(zmq.SUBSCRIBE, topic)
        self._subscriber = subscriber
        self._quit_event = multiprocessing.Event() if event is None else event
        self._queue = collections.deque(maxlen=1)
        self._listeners = []

    def add_listener(self, c):
        self._listeners.append(c)

    def get_latest(self):
        return self._queue[0] if bool(self._queue) else None

    def pop_latest(self):
        return self._queue.popleft() if bool(self._queue) else None

    def quit(self):
        self._quit_event.set()

    def run(self):
        while not self._quit_event.is_set():
            try:
                _latest = json.loads(receive_string(self._subscriber).split(':', 1)[1])
                self._queue.appendleft(_latest)
                list(map(lambda x: x(_latest), self._listeners))
            except zmq.Again:
                pass


class CameraThread(threading.Thread):
    def __init__(self, url, event, topic=b'', hwm=1, receive_timeout_ms=25):
        super(CameraThread, self).__init__()
        subscriber = zmq.Context().socket(zmq.SUB)
        subscriber.set_hwm(hwm)
        subscriber.setsockopt(zmq.RCVTIMEO, receive_timeout_ms)
        subscriber.setsockopt(zmq.LINGER, 0)
        subscriber.connect(url)
        subscriber.setsockopt(zmq.SUBSCRIBE, topic)
        self._subscriber = subscriber
        self._quit_event = event
        self._images = collections.deque(maxlen=1)

    def capture(self):
        return self._images[0] if bool(self._images) else (None, None)

    def run(self):
        while not self._quit_event.is_set():
            try:
                [_, md, data] = self._subscriber.recv_multipart()
                md = json.loads(md)
                height, width, channels = md['shape']
                img = np.frombuffer(buffer(data), dtype=np.uint8)
                img = img.reshape((height, width, channels))
                self._images.appendleft((md, img))
            except ValueError as e:
                logger.warning(e)
            except zmq.Again:
                pass

# Class that sends and receives data to/from clients
class JSONServerThread(threading.Thread):
    def __init__(self, url, event, hwm=1, receive_timeout_ms=50):
        super(JSONServerThread, self).__init__()
        server = zmq.Context().socket(zmq.REP)
        server.set_hwm(hwm)
        server.setsockopt(zmq.RCVTIMEO, receive_timeout_ms) # Will shutdown socket after 50ms pass with no message
        server.setsockopt(zmq.LINGER, 0) # Does not linger at all after shutting down
        server.bind(url)
        self._server = server
        self._quit_event = event
        self._queue = collections.deque(maxlen=1)
        self._listeners = []
        self.message_to_send = None

    # Adds a listener function to be executed whenever the server gets a message
    def add_listener(self, c):
        self._listeners.append(c)

    # Function that executes everytime the server receives a message.
    # Stores the message to its internal queue, then runs each listener function appended from add_listener(), with the message received as a argument
    def on_message(self, message):
        self._queue.appendleft(message)
        list(map(lambda x: x(message), self._listeners))

    # Returns the stored data
    def get_latest(self):
        return self._queue[0] if bool(self._queue) else None

    # Returns the stored data and then deletes it from the queue
    def pop_latest(self):
        return self._queue.popleft() if bool(self._queue) else None

    # Returns an empty dictionary if we want to send back nothing, or send back our own message to the client
    def serve(self, reply):
        if reply is None:
            return {}
        return {reply}

    # Main function of the class.
    # Receives data from the client, and sends back a reply based on self.message_to_send
    def run(self):
        while not self._quit_event.is_set():
            try:
                message = json.loads(receive_string(self._server))
                self.on_message(message)
                send_string(self._server, json.dumps(self.serve(self.message_to_send)))
            except zmq.Again:
                pass


class LocalIPCServer(JSONServerThread):
    def __init__(self, name, url, event, receive_timeout_ms=50):
        super(LocalIPCServer, self).__init__(url, event, receive_timeout_ms)
        self._name = name
        self._m_startup = collections.deque(maxlen=1)
        self._m_capabilities = collections.deque(maxlen=1)

    def register_start(self, errors, capabilities=None):
        capabilities = {} if capabilities is None else capabilities
        self._m_startup.append((datetime.datetime.utcnow().strftime('%b %d %H:%M:%S.%s UTC'), errors))
        self._m_capabilities.append(capabilities)

    def serve(self, message):
        try:
            if message.get('request') == 'system/startup/list' and self._m_startup:
                ts, errors = self._m_startup[-1]
                messages = ['No errors']
                if errors:
                    d_errors = dict()  # Merge to obtain distinct keys.
                    [d_errors.update({error.key: error.message}) for error in errors]
                    messages = ['{} - {}'.format(k, d_errors[k]) for k in d_errors.keys()]
                return {self._name: {ts: messages}}
            elif message.get('request') == 'system/service/capabilities' and self._m_capabilities:
                return {self._name: self._m_capabilities[-1]}
        except IndexError:
            pass
        return {}


# Class that connects to a url of a server and sends a message first, then receives a reply
class JSONZmqClient(object):
    def __init__(self, urls, hwm=1, receive_timeout_ms=200):
        self._urls = urls if isinstance(urls, list) else [urls]
        self._receive_timeout = receive_timeout_ms
        self._context = None
        self._socket = None
        self._hwm = hwm
        self._create(self._urls)

    def _create(self, locations):
        context = zmq.Context()
        socket = context.socket(zmq.REQ) # socket zmq.REQ will block on send unless it has successfully received a reply back
        socket.set_hwm(self._hwm)
        socket.setsockopt(zmq.RCVTIMEO, self._receive_timeout) # Socket closes after 200ms
        socket.setsockopt(zmq.LINGER, 0) # Socket does not linger after a command to shut it down. It shuts down immediately.
        [socket.connect(location) for location in locations] # Connects to all urls it got as an argument
        self._context = context
        self._socket = socket

    def quit(self):
        if self._context is not None:
            self._context.destroy()

    # Main function of the class.
    def call(self, message):
        ret = {}
        # For each url it is connected to
        for i in range(len(self._urls)):
            try:
                # Sends a message
                send_string(self._socket, json.dumps(message), zmq.NOBLOCK)

                # Receives a reply and stores it in the "ret" dictionary
                ret.update(json.loads(receive_string(self._socket)))
            except zmq.ZMQError:
                j = i + 1
                self._create(self._urls[j:] + self._urls[:j])
        return ret