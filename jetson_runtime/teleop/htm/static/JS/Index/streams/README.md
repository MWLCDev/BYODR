# MJPEG Stream Controller

## Introduction

This JavaScript module manages MJPEG (Motion JPEG) video streaming for front and rear cameras in a web application. It handles frame rate control, JPEG quality adjustments, WebSocket communication with the cameras, and rendering of the video streams onto the webpage. The module is designed to provide a smooth streaming experience while optimizing bandwidth and performance.

## Architecture Overview

The code consists of several classes and functions that work together to manage MJPEG streaming:

### Classes

#### 1. `MJPEGFrameController`

- **Purpose**: Controls the frame rate and JPEG quality adjustments for MJPEG streams.
- **Key Properties**:
  - `targetTimeout`: Time until the next frame capture.
  - `timeSmoothing`: Smoothing factor for frame rate adjustments.
  - `actualFps`: The actual frames per second being captured.
  - `targetFps`: The desired frames per second.
  - `duration`: Smoothed duration between frames.
  - `jpegQuality`: Current JPEG quality level.
- **Key Methods**:
  - `setTargetFps(fps)`: Sets the desired frame rate.
  - `getActualFps()`: Retrieves the current actual frame rate.
  - `updateFramerate()`: Adjusts the frame rate and JPEG quality based on performance.

#### 2. `MJPEGControlLocalStorage`

- **Purpose**: Manages JPEG quality settings and persists them using `localStorage`.
- **Key Properties**:
  - `minJpegQuality`: Minimum allowable JPEG quality.
  - `maxJpegQuality`: Maximum allowable JPEG quality.
- **Key Methods**:
  - `setMaxQuality(val)`: Sets the maximum JPEG quality and adjusts the minimum accordingly.
  - `increaseQuality()`: Increases the maximum JPEG quality.
  - `decreaseQuality()`: Decreases the maximum JPEG quality.
  - `load()`: Loads the JPEG quality settings from `localStorage`.
  - `save()`: Saves the JPEG quality settings to `localStorage`.

#### 3. `RealCameraController`

- **Purpose**: Manages the communication with a real camera via WebSocket.
- **Key Properties**:
  - `cameraPosition`: Position of the camera ('front' or 'rear').
  - `frameController`: An instance of `MJPEGFrameController`.
  - `messageCallback`: Callback function to handle incoming messages (frames).
  - `socket`: The WebSocket connection to the camera.
- **Key Methods**:
  - `capture()`: Requests a new frame from the camera.
  - `setRate(rate)`: Sets the frame capture rate ('fast', 'slow', 'off').
  - `startSocket()`: Initiates the WebSocket connection to the camera.
  - `stopSocket()`: Terminates the WebSocket connection and clears timers.
  - **Timers**:
    - `socketCaptureTimer`: Manages when to request the next frame.
    - `socketCloseTimer`: Manages the timeout for server response.

#### 4. `MJPEGPageController`

- **Purpose**: Manages MJPEG settings and interactions with the webpage elements.
- **Key Properties**:
  - `store`: Instance of `MJPEGControlLocalStorage`.
  - `cameraInitListeners`: Listeners for camera initialization events.
  - `cameraImageListeners`: Listeners for receiving camera images.
  - `elPreviewImage`: jQuery element for the preview image.
  - `expandCameraIcon`: jQuery element for the expand camera icon.
- **Key Methods**:
  - `init(cameras)`: Initializes the page controller with camera controllers.
  - `bindDomActions()`: Binds UI elements to their respective event handlers.
  - `refreshPageValues()`: Updates the UI with current settings.
  - `addCameraListener(cbInit, cbImage)`: Registers listeners for camera events.
  - `notifyCameraInitListeners(cameraPosition, cmd)`: Triggers camera init listeners.
  - `notifyCameraImageListeners(cameraPosition, blob)`: Triggers image listeners.
  - `applyLimits()`: Applies JPEG quality limits to all cameras.
  - `setCameraFramerates(position)`: Adjusts camera frame rates based on active camera.

#### 5. `MJPEGApplication`

- **Purpose**: Main application class for MJPEG management.
- **Key Properties**:
  - `mjpegPageController`: Instance of `MJPEGPageController`.
  - `frontCameraFrameController`: Instance of `MJPEGFrameController` for the front camera.
  - `rearCameraFrameController`: Instance of `MJPEGFrameController` for the rear camera.
  - `mjpegRearCamera`: Instance of `RealCameraController` for the rear camera.
  - `mjpegFrontCamera`: Instance of `RealCameraController` for the front camera.
- **Key Methods**:
  - `init()`: Initializes the application.
  - `createCameraConsumer(cameraPosition)`: Creates a consumer function for camera data.
  - `findCanvasAndExecute()`: Locates the canvas element and initializes rendering.
  - `initializeApplication(canvas)`: Sets up the application with the canvas element.
  - `setupStreamTypeSelector()`: Configures the stream type selector UI element.
  - `setupCameraActivationListener()`: Sets up listener for camera activation changes.
  - `setupMJPEGCanvasRendering(canvas)`: Handles rendering of MJPEG streams onto the canvas.
  - `startAll()`: Starts all MJPEG streams.
  - `stopAll()`: Stops all MJPEG streams.
  - `findCanvasAndRebind()`: Re-binds canvas and image elements if needed.

### Data Flow

1. **Initialization**:
   - `MJPEGApplication.init()` is called.
   - Camera controllers (`RealCameraController`) are created for both front and rear cameras.
   - The application searches for the canvas element and initializes rendering.

2. **WebSocket Communication**:
   - `RealCameraController.startSocket()` establishes a WebSocket connection to the camera.
   - On receiving a message (`ws.onmessage`), it processes the data (image or command).

3. **Frame Capture and Rendering**:
   - `RealCameraController.capture()` requests a frame from the camera.
   - The frame controller (`MJPEGFrameController`) adjusts the frame rate and JPEG quality.
   - Images are rendered onto the canvas or preview image by the `MJPEGPageController`.

4. **User Interaction**:
   - Users can adjust JPEG quality using UI controls.
   - Users can toggle between cameras and expand the preview image.

## Cautions and Considerations

- **WebSocket Stability**: Ensure that the WebSocket server is stable and handles reconnections gracefully. The `RealCameraController` attempts to reconnect if the connection is lost.
- **Performance**: Adjusting the JPEG quality and frame rates can impact performance and bandwidth usage. The application tries to balance quality and performance using the `MJPEGFrameController`.
- **Browser Compatibility**: Test the application in different browsers to ensure compatibility, especially with WebSocket and canvas support.
- **Error Handling**: The code includes try-catch blocks to handle exceptions. Monitor the console for error messages to troubleshoot issues.
- **Resource Cleanup**: The application clears timers and closes sockets to prevent memory leaks. Ensure that `stopAll()` is called when the application is unloaded or the user navigates away.
