# Nano Runtime

## Overview

The **Jetson Nano Runtime** handles computationally intensive tasks such as inference, video streaming, and network management within the **BYODR** project.

## Docker Services

The Jetson Nano runs the following Docker services:

### 1. HTTPD

- **Input**: Listens for data requests from `Teleop`, `Pilot`, `Stream1`, and `Stream0`. These sources are listed in the configuration file (`haproxy.conf`) used by the proxy server.
- **Function**: This service sets up a proxy server using HAProxy to balance load and forward requests.
- **Output**: Forwards requests to the specified services, optimizing data flow and managing traffic.
- **Configuration**: Configured using `haproxy.template` and `haproxy_ssl.template` located in `httpd/certs/`.

### 2. Inference

- **Input**:
  - Stream from the AI camera with the socket URL `ipc:///byodr/camera_0.sock`.
  - Routes from `Teleop` with the socket URL `ipc:///byodr/teleop.sock`.
  - Timestamps from `Teleop` with the socket URL `ipc:///byodr/teleop_c.sock`.
- **Function**: Uses a trained AI model to generate steering angles and make predictions based on image data from the AI camera. Overrides the self-driving directions when input is received from `Teleop`.
- **Outputs**:
  - Sends commands to the `Servos` service for motor control.
  - Initiates an IPC server at `ipc:///byodr/inference_c.sock`.
  - Uses a JSON publisher at `ipc:///byodr/inference.sock` to broadcast data.
- **Files**: Model files are stored in `inference/models/`.

### 3. Teleop

- **Inputs**:
  - Receives streams from `Stream0` and `Stream1` services on the Pi.
  - Receives JSON data from `Pilot`, `Vehicle`, and `Inference` services.
  - Receives control input from the operator.
- **Function**: Acts as the central control point, translating user input into robot commands and managing live video streams. This service also encodes video streams into MJPEG for web display.
- **Outputs**:
  - Robot movement based on user commands.
  - Live video feed to the web app.
  - Logs and messages stored in `MongoDB`.
- **Files**: Web server files can be found in `teleop/htm/`.

### 4. Vehicle

- **Inputs**:
  - JSON data from the `Pilot` service.
  - JSON data from the `Teleop` service.
- **Function**: Sets up a server to connect with a CARLA simulator, which is used to simulate the robot's behavior in a virtual environment.
- **Outputs**: Sends data to a server running an instance of CARLA, representing a segment inside the simulation.
- **Questions**:
  - Is this service solely for communicating with the CARLA simulator?
  - Where is the CARLA simulation hosted?
  - What do the video streams from the server do?

### 5. ROS Node

- **Inputs**:
  - JSON data from the `Pilot` service.
  - JSON data from the `Teleop` service.
- **Function**: Defines a ROS2 node, facilitating communication between the `Teleop` node and the `Pilot` node. It controls the driving mode (Autopilot or Manual) based on user input and adjusts the segment's max speed.
- **Output**: Publishes ROS commands in JSON format to the `Pilot` service.

### 6. Pilot

- **Inputs**:
  - JSON data from `Teleop`, `ROS Node`, `Vehicle`, and `Inference` services.
  - IPC chatter from `Teleop`.
- **Function**: Controls the segment's autonomous movement using a pre-trained AI model. Sets up a JSON publisher and local IPC server to share data with other services.
- **Output**: Sends JSON commands to the `Servos` service for autonomous driving.

### 7. Zerotier

- **Function**: Adds the Jetson Nano to a secure P2P virtual network, allowing it to communicate with other nodes.
- **Output**: Enables secure connection with other segments in the ZeroTier network.
- **Input**: Configured through command-line inputs.
- **Note**: Works in conjunction with WireGuard for added security.

### 8. WireGuard

- **Input**: Manages network data from the Jetson Nano and Router.
- **Function**: Encrypts all communication to enhance security during data transmission.
- **Output**: Secures all outgoing and incoming data.
- **Why Use WireGuard and ZeroTier?**: WireGuard focuses on encryption, while ZeroTier manages network connections between devices, providing a layered security approach.

### 9. MongoDB

- **Input**: Receives logs and data from `Teleop` and other services.
- **Function**: Stores logs and data in a local MongoDB instance.
- **Output**: Provides a structured storage for logs that can be accessed by other services.
- **Configuration**: Located in `mongodb/wrap.py`.

### 10. FTPD

- **Input**: Receives newly trained models from the training server.
- **Function**: Sets up a Pure-FTPd server for managing model data. Facilitates the transfer of models to/from the training server.
- Create an FTP server that exposes three folder to the user `Autopilot`, `Models` and `photos`. The user can download the training sessions file from the Autopilot folder after the robot is done with making the compressed file.
- **Files**: Configuration scripts are found in `ftpd/`.
- **Questions**:
  - Is this service the link between the Nano and Firezilla FTP server? Yes

### 11. Following

- **Input**: Gets starting and stopping command from `teleop`  .
- **Function**: Make the robot follow a person in front of it.
- **Output**: Sends movement command to `vehicle` service as it streamlines the commands from different services to it.
