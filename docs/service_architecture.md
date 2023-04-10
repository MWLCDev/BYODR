# Service Architecture

Smart Segment
A smart segment is part of the robot that houses computer systems inside that allow it to move autonomously. Connected segments make the robot act like a caterpillar.
This computer system includes a Raspberry Pi, a Jetson Nano, 2 cameras, a router and 2 motor controllers.

## Hardware

### AI Camera (camera0)

- A smart segment uses Hikvision PTZ Dome Network camera for its AI Camera.

- IP: 192.168.1.64

- **Input**: Footage from its surroundings

- **Output**: Sends H264 encoded video ouput to the Pi’s Docker container service called “Stream0”.

### Operator Camera (camera1)

- The smart segment also uses a 2nd Hikvision PTZ Dome Network camera for an Operator Camera.

- IP: 192.168.1.65

- **Input**: Footage from its surroundings

- **Output**: Sends H264 encoded video output to the Pi’s Docker container service called "Stream1".

### Raspberry Pi 4B

- OS: balena-cloud-byodr- pi-raspberrypi4-64-2.99.27-v14.0.8
- IP: 192.168.1.32
- This OS allows it to communicate with Balena Cloud. Inside the Pi, there are 5 processes running, 4 of which run in their own separate Docker containers.

### Nvidia Jetson Nano

- OS: balena-cloud-byodr-nano-jetson-nano-2.88.4+rev1-v12.11.0
- IP: 192.168.1.100
- This OS allows it to communicate with Balena Cloud. Inside the Nano, there are 10 processes running, all of which run in their own separate Docker containers.

### RUT-955

- IP: 192.168.1.1
- The router inside the segment is called RUT955 from Teltonika. The router has LAN, WAN, 4G, 5G and LTE capabilities. It's ethernet connectivity is extended with a switch. The router is responsible for all internet connectivity between the segment and the rest of the Internet.
- This router also includes an internal relay that works as a switch that lets the battery power the rest of the segment. Only when the router is booted up and the relay switch closes, will the segment receive power to the rest of its internal components.

### Motor Controller 1

- The segment uses the Mini FSESC6.7 from Flipsky. It is connected via USB to the ttyACM0 serial port of the Pi.
- **Input**: Commands from the Pi.
- **Output**: Sends power to its respective motor wheel in order to turn it according to its commands.

### Motor Controller 2

- The segment uses the Mini FSESC6.7 from Flipsky. It is connected via USB to the ttyACM1 serial port of the Pi.
- **Input**: Commands from the Pi.
- **Output**: Sends power to its respective motor wheel in order to turn it according to its commands.

## Software stack

1. #### Balena

From Balena, we use their Balena Cloud services, and also use BalenaOS on the Raspberry Pi and Jetson Nano, to make them compatible with Balena Cloud. From the Balena Cloud we can upload new versions of software, update segments OTA, reboot, connect via SSH, and manage segments remotely.

2. #### Docker

Docker is a platform for building, shipping, and running applications in containers. Containers are lightweight, portable, and self-sufficient units that contain all the necessary software, libraries, and dependencies to run an application. Docker enables developers to package their applications into containers, which can be easily deployed and run on any platform that supports Docker. With Docker, developers can ensure that their applications run consistently across different environments, from development to production.

The BYODR project includes docker files that can be used to build a Docker image for each service as well as instructions on how to deploy the image onto a robot using Balena Cloud. By using this approach, users can ensure that the software stack is consistent and reproducible across multiple robots, and can easily deploy updates and manage their fleet of cars from a central location.

3. #### Zerotier

Zerotier is a "freemium" P2P (Peer to Peer) VPN service that allows devices with internet capabilities to securely connect to P2P virtual software-defined networks. 

The Pi has a Zerotier instance running inside it. This means that it is equipped to work with a Zerotier client that is running on our devices, so that we can add the Pi to our VPN network.

Similarly to the Pi, the Nano also has the same functionality regarding Zerotier, although arguably more important here, since it allows the User to connect to the Nano, and by extension the Web server, via a secure zerotier network.

4. #### Wireguard

Similarly to Zerotier, Wireguard is also a VPN. The difference here is that Wireguard is used by the Nano in every network procedure it has to go through for safety. Since the Nano has plenty more processes that require a network connection, compared to the Pi, Wireguard is an extra layer of security against attacks. This process is running inside a docker container.

**Q1**: Why do we use Wireguard if we have ZT?
**A1**: Since ZeroTier and WireGuard look similar, the project uses both ZeroTier and WireGuard for different purposes. ZeroTier is used to create a secure network connection between the robot and the user's computer, while WireGuard is used to encrypt the data that is transmitted over that connection. Together, these technologies provide a secure and reliable way for users to remotely control the robots.

# The CPUs

This section will explaining each part of the CPUs, how is it working and the service inside of it

## Raspberry Pi docker services:

### Stream0

**Input**: Receives video stream from the AI camera.

**Function**:  Creates a high quality H264 video output stream

**Output**: Sends the stream via RTSP to the web server located in Teleop.

**Q1**: Why does the Pi create the streams, and not just send them from the cameras directly to the nano, bypassing the Pi?



### Stream1

**Input**: Receives video stream from the Operator camera.

**Purpose**: Similarly to the process above, it creates a high quality H264 video output stream.

**Output**: Sends the stream via RTSP to the web server located in Teleop.

**Q1**: How does the AI get the images for itself? From the H264 stream, or someplace else?

### Zerotier

**Input**: Receives input from the user, using the built-in command line.

**Function**: We can add the Pi to our VPN network.

**Output**: The Pi can communicate with the software-defined virtual networks that the user has built, via the internet.

**Q1**: Why does the Pi need the zerotier?

### Servos

**Input**: Receives commands in JSON format from Teleop, Inference, Pilot that request movement from the motors. 

**Function**: Sets up a JSON server that listens on `0.0.0.0:5555` for commands from other processes. Listening to `0.0.0.0` means listening from anywhere that has network access to this device. It also sets up  a JSON Publisher so that this service can send JSON data to any services that are listening to this service. Decodes commands received from the other services are decoded and stored in a deque.

This service also initiates an http server listening to port `9101` (default option).

**Output**: The commands are sent to the motor controllers via the serial USB connection.

**Q1**: BalenaCloud lists another service called "pigpiod". This service and the "servos" service both use the same image in their docker container. What does the pigpiod service do?

**Q2**: Why does this service have a JSON publisher? Who does it send data to?

### Battery Management System (BMS) [The only service that does not run in a docker container]

**Input**: Receives data from the BMS inside the battery itself.

**Function**: The Pi uses an I2C Pi Hat to communicate with the special battery that the segment uses. From here, the Pi can give a "pulse" to the battery in order to "reset" it. This system also allows for seamless use of 2 or more of the same battery, on the same segment. This process is exclusively hardware based, so it is not running in a container.

**Output**: Sends data to the BMS inside the battery.

## Jetson Nano docker services:

### HTTPD

**Input**: Listens for data requests from Teleop, Pilot, Stream1, Stream0. The sources are listed in the configuration file (called haproxy.conf) that the proxy server uses.

**Function**: This service sets up a proxy server (Intermediate server between the client and the actual HTTP server) using HAProxy, for load balancing and request forwarding.

**Output**: Forwards requests to the same services as above, but taking into account load balancing. The destinations are listed in the configuration files that the proxy server uses.

### Inference

**Input 1**: Receives stream from AI camera with the socket url being ``'ipc:///byodr/camera_0.sock'``
**Input 2**: Receives routes from teleop with the socket url being ``'ipc:///byodr/teleop.sock'``
**Input 3**: Receives timestamps from teleop with the socket url being ``'ipc:///byodr/teleop_c.sock'``

**Function**: This service is responsible for an interface for generating steering angles and making predictions based on images. These actions are based on a trained neural network model. If this service has input from Teleop, they override the self-driving directions of the model.
This service also initiates an IPC server with url ``'ipc:///byodr/inference_c.sock'``, and a JSON publisher with url ``'ipc:///byodr/inference.sock'``

**Output 1**: Sends the AI model's current state (predicted action, obstacle avoidance, penalties, and other navigation-related information) to the local JSON Publisher.
**Output 2**: Creates list with any errors from this service. The list will be send to the Teleop service upon request.
**Q1**: How does Inference, Pilot and Teleop work together, if they work together?
**Q2**: How does Inference send its data to the Pi for proper movement?

### Zerotier

**Input**: Receives input from the user, using the buildin command line.

**Function**: The Nano can be added into a virtual network.

**Output**: Can communicate securely with nodes of the same network.

### WireGuard (Not used)

**Input**: Receives data from the Nano and the Router.

**Function**: Encrypts the data of the Nano.

**Output**: The data send by the Nano towards the internet are encrypted.

**Q**: Why do we use Wireguard if we have ZT?

**A**: Since ZeroTier and WireGuard look similar, the project uses both ZeroTier and WireGuard for different purposes. ZeroTier is used to create a secure network connection between the robot and the user's computer, while WireGuard is used to encrypt the data that is transmitted over that connection. Together, these technologies provide a secure and reliable way for users to remotely control the robots.

### Teleop

**Input 1**: Receives stream from Stream0 (Camera0-AI) service of the Pi `'ipc:///byodr/camera_0.sock'`.

**Input 2**: Receives stream from Stream1 (Camera1 - Operation) service of the Pi `'ipc:///byodr/camera_1.sock'`.

**Input 3**: Receives data in a JSON format from the Pilot service, that includes the proper action for the segment to take, depending on various factors. Potential actions are:

1. Switch to manual driving mode
2. Continue with the current manual mode commands that are being executed
3. Continue with the current autopilot mode commands that are being executed
4. Continue with the current backend(Carla simulation) mode commands that are being executed

Note, those commands could be old, repeated or empty commands (do nothing)

**Input 4**: Receives the current state (location, speed, timestamp and more) of the segment that is located in the Carla simulation, in a JSON format from the Vehicle service

**Input 5**: Receives the AI model’s current state in a JSON format from the Inference service’s Output 1.

**Input 6**: Receives input from the Operator's method of control.

**Input 7**: Receives lists of errors and/or capabilities from the following services from respective sockets:

- Pilot service via `ipc:///byodr/pilot_c.sock`
- Inference service via `ipc:///byodr/inference_c.sock`
- Vehicle service via `ipc:///byodr/vehicle_c.sock`

**Function**: This service includes a web server that listens for inputs from multiple sources that are later used to move the robot. The key presses from the operator are registered and reflected upon the robot using this service.
This service includes a logger that logs information regarding the manual control of the robot. 
In addition, there is a function in this server that encodes the streams from the cameras to MJPEG.
It also hosts the site design files necessary to draw the Web App.

**Output 1**: Robot movement according to user's commands
**Output 2**: Live video feed on the web app
**Output 3**: MJPEG stream capability
**Output 4**: Logs and messages produced during operation are stored MongoDB.
**Output5**: Publishes the segment's selected route on its JSON Publisher.
**Output6**: Publishes a timestamp with a 'restart' command on its JSON Publisher

**Q1**: How does "Teleop" translate user input into robot movement?
**Q2**: How does it communicate with the cameras, "Pilot", "Inference" and "Vehicle"?
**Q3**: What data does it receive and send to the Pilot, Vehicle and Inference services?
**Q4**: From where does it receive its navigation images?
**Q5**: What does it do with the images?

### Vehicle

**Input 1**: Receives a JSON from the Pilot service, that includes the proper action for the segment to take, depending on various factors. Potential actions are:

- Switch to manual driving mode
- Continue with the current manual mode commands that are being executed
- Continue with the current autopilot mode commands that are being executed
- Continue with the current backend(Carla simulation) mode commands that are being executed

**Input 2**: Receives the timestamp with a 'restart' command from Output 6 of Teleop.
**Input 3**: Receives a route from Teleop's Output 5

**Function**: This process sets up a server that connects to a CARLA simulator and communicates with it to control a self-driving car. Carla is an open-source simulator for autonomous driving research. It is used to simulate the robot’s behavior in a virtual environment.
**Output 1**: Publishes the current state (location, speed, timestamp and more) of the segment that is located in the Carla simulation, in the JSON Publisher.
**Output 2:** Creates list with any errors and capabilities of the simulated segment. The list will be send to the Teleop service upon request.

**Q1**: Is this process exclusively used to send data to the CARLA simulator, and nothing else regarding the driving of the robot?
**Q2**: Where is the CARLA simulation hosted?
**Q3**: What do the video streams created in the server do exactly?

### ROS Node

**Input 1**: Receives a JSON from the Pilot service, that includes the proper action for the segment to take, depending on various factors. Potential actions are:

- Switch to manual driving mode
- Continue with the current manual mode commands that are being executed
- Continue with the current autopilot mode commands that are being executed
- Continue with the current backend(Carla simulation) mode commands that are being executed

**Input 2**: Receives the timestamp with a 'restart' command from Output 6 of Teleop
**Function**: This service defines a ROS2 node which connects to a teleop node and a pilot node, and switches the driving mode to Autopilot or Manual, depending on user input. It also sets a max speed for the segment.
**Output**: Sends ROS commands in JSON format to the Pilot service
**Q1**: Why exactly do we need this service?
**Q2**: Does the communication with other services imply the existence of multiple nodes?
**Q3**: Why does it publish json data only to the Pilot, and not to both Pilot and Teleop?
**Q4**: What is "m" and what does it include?

### Pilot

**Input 1**: Receives a route from Teleop's Output 5
**Input 2**: Receives"m"from ROS node's Output 1
**Input 3**: Receives the current state (location, speed, timestamp and more) of the segment that is located in the Carla simulation from Vehicle's Output 1.
**Input 4**: Receives the AI model's current state (predicted action, obstacle avoidance, penalties, and other navigation-related information) from Inference's Output 1
**Input 5**: Receives the timestamp with a 'restart' command from Output 6 of Teleop
**Input 6: **Receives user input (????????????)

**Function**: This process sets up a JSON publisher and a local IPC server to send data to other services that have JSON collectors. It also is responsible for controlling the segment’s autonomous movement by using a pre-trained AI model.
**Output 1** : Receives a JSON from the JSON Publisher, that includes the proper action for the segment to take, depending on various factors. Potential actions are:

- Switch to manual driving mode
- Continue with the current manual mode commands that are being executed
- Continue with the current autopilot mode commands that are being executed
- Continue with the current backend(Carla simulation) mode commands that are being executed

**Output 2**: Creates list with any errors from this service. The list will be send to the Teleop service upon request.
**Output 3**: Movement commands to the Pi. (???)

**Q1**: This process is exclusively used by the robot for its autonomous driving?
**Q2**: How does this service cooperate with "Inference"?
**Q3**: Why does this service start an HTTP server?
**Q4**: What is an IPC chatter json receiver?
**Q5**: What is a local ipc server? (It uses _c in its name => c = chatter?)
**Q6**: How does this service send movement commands to the Pi? (If it does)

### MongoDB

**Input**: Receives data from the segment, and stores any and all logs produced by the other services (?)
**Function**: This service creates a default MongoDB user and starts a configurable MongoDB server on the local machine.
**Output**: Stores logs in its built in database
**Q1**: What does the DB store inside it?
**Q2**: How does the DB get the data that it stores?

### FTPD

**Input**: Receives the newly trained model from the training server.
**Function**: This service creates a Pure-FTPd Server with a predefined set of commands. This server is used to send its training data to the server, and similarly, receive the trained model from the server.
**Output**: Sends data to the AI training server with parameters for its specific training.
**Q1**: Is this the code that connects the Nano to the FileZilla FTP server? (Mentioned in the read the docs)
**Q2**: How does this ftp server store, send and receive data from the training server?

# General questions

**Q1**: How json receivers and publishers work? Because this is used to send data one to another.
**Q2**: If all segments are in a zerotier network, does any data sent between the segments encrypted?