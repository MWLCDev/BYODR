# Pi4 Runtime

## Overview

The **Raspberry Pi 4B Runtime** manages essential control and communication tasks for the **BYODR** project on a low level, including video streaming, and motor control.

## Docker Services

The Raspberry Pi runs the following Docker services:

### 1. Servos

- **Input**: Receives movement commands in JSON format from  `Pilot`.
- **Function**: Controls the motor controllers connected via `ttyACM0` and `ttyACM1` serial ports.
- **Output**: Sends commands to the motor controllers for movement.
- **Files**: Configuration and server scripts are in `servos/`.
- with every command sent from `Pilot`, it will broadcast a message about the current speed of the vehicle

### 2. Stream0

- **Input**: Receives video stream from the AI camera (`camera0`) at `192.168.1.64`.
- **Function**: Encodes the video stream into H264 format.
- **Output**: Sends the stream via RTSP to the `Teleop` service on the Jetson Nano.
- **Why Not Direct?**: The Pi preprocesses the video stream to reduce the load on the Nano.

### 3. Stream1

- **Input**: Receives video stream from the Operator camera (`camera1`) at `192.168.1.65`.
- **Function**: Encodes the video stream into H264 format.
- **Output**: Sends the stream via RTSP to the `Teleop` service on the Jetson Nano.
- **Files**: Stream configurations are located in `stream/camera.template`.

### 4. Zerotier

- **Function**: Adds the Raspberry Pi to a secure P2P network for remote access.
- **Output**: Establishes a secure connection with other segments and the user.
