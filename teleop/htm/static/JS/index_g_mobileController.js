let ws;
window.addEventListener('load', () => {
  let ws_protocol = document.location.protocol === 'https:' ? 'wss://' : 'ws://';
  let ws_url = `${ws_protocol}${document.location.hostname}:${document.location.port}/ws/send_mobile_controller_commands`;
  ws = new WebSocket(ws_url);

  ws.onopen = function (event) {
    console.log('Mobile controller (WS) connection opened');
  };

  //Check the respond from the endpoint. If the user is operator or viewer 
  // ws.onmessage = function (event) {
  //   // Handle the received data as needed
  //   // console.log('Message received:', event.data);
  // };

  ws.onerror = function (error) {
    console.log('WebSocket Error:', error);
  };

  ws.onclose = function (event) {
    console.log('Mobile controller (WS) connection closed');
  };

  console.log('Created Mobile controller (WS)');
});

class Triangle {
  static textStyle = new PIXI.TextStyle({
    fill: 'white',
    fontSize: 20,
    align: 'center',
  });

  constructor(direction = 'up', text = '') {
    this.direction = direction;
    this.text = text;
    this.container = new PIXI.Container();
    this.graphics = new PIXI.Graphics();
    this.container.addChild(this.graphics);
    if (text) {
      this.textObj = new PIXI.Text(text, Triangle.textStyle);
      this.textObj.anchor.set(0.5, 1);
      this.graphics.addChild(this.textObj);
    }
    this.updateDimensions();
    this.drawTriangle();
  }

  updateDimensions() {
    this.height = window.innerHeight / 4;
    this.baseWidth = 2 * (this.height / Math.sqrt(3));
    if (this.baseWidth > 0.6 * 1000) {
      this.baseWidth = 0.6 * 1000;
      this.height = (this.baseWidth * Math.sqrt(3)) / 2;
    }
  }
  /**
   * Draw an upper or lower triangle depending on this.direction var. The triangles will have a gap between them
   * @param {number} yOffset the position for the tip of the triangle
   */
  drawTriangle(yOffset = 0) {
    this.graphics.clear();
    this.graphics.beginFill(0x000000);
    const midScreen = window.innerHeight / 2;

    // Simplify the yOffset adjustment
    const yOffsetAdjustment = this.direction === 'up' ? -5 : 5;

    if (this.direction === 'up') {
      this.vertices = [
        [(window.innerWidth - this.baseWidth) / 2, yOffset + midScreen - this.height + yOffsetAdjustment],
        [(window.innerWidth + this.baseWidth) / 2, yOffset + midScreen - this.height + yOffsetAdjustment],
        [window.innerWidth / 2, yOffset + midScreen + yOffsetAdjustment],
      ];
    } else {
      this.vertices = [
        [(window.innerWidth - this.baseWidth) / 2, yOffset + midScreen + this.height + yOffsetAdjustment],
        [(window.innerWidth + this.baseWidth) / 2, yOffset + midScreen + this.height + yOffsetAdjustment],
        [window.innerWidth / 2, yOffset + midScreen + yOffsetAdjustment],
      ];
      if (this.textObj) {
        // Extra pixels is the gap the text will have with the bottom side of the triangle 
        this.textObj.position.set(window.innerWidth / 2, yOffset + midScreen + this.height - 10);
      }
    }
    this.graphics.drawPolygon(this.vertices.flat()); // Add this to render the triangle
    this.graphics.endFill();
  }
}

class Dot {
  constructor() {
    this.graphics = new PIXI.Graphics();
    this.drawDot(0, 0); // initial position
  }

  drawDot(x, y) {
    this.graphics.clear();
    this.graphics.beginFill(0xffffff); // color for the dot
    this.graphics.drawCircle(x, y, 18); // The radius is 18 (was requested to have diameter of 10mm === 36px)
    this.graphics.endFill();
  }

  setPosition(x, y) {
    this.drawDot(x, y);
  }

  remove() {
    this.graphics.clear();
  }
}
/**
 * Check if a point is inside a triangle using barycentric
 * @param {number} px Point's x-coord
 * @param {number} py Point's Y-coord
 * @param {number} ax Triangle's 1st edge x-coord
 * @param {number} ay Triangle's 1st edge y-coord
 * @param {number} bx Triangle's 2nd edge x-coord
 * @param {number} by Triangle's 2nd edge y-coord
 * @param {number} cx Triangle's 3rd edge x-coord
 * @param {number} cy Triangle's 3rd edge y-coord
 * @returns 
 */
function pointInsideTriangle(px, py, ax, ay, bx, by, cx, cy) {
  // Compute vectors
  const v0 = [cx - ax, cy - ay];
  const v1 = [bx - ax, by - ay];
  const v2 = [px - ax, py - ay];

  // Compute dot products
  const dot00 = v0[0] * v0[0] + v0[1] * v0[1];
  const dot01 = v0[0] * v1[0] + v0[1] * v1[1];
  const dot02 = v0[0] * v2[0] + v0[1] * v2[1];
  const dot11 = v1[0] * v1[0] + v1[1] * v1[1];
  const dot12 = v1[0] * v2[0] + v1[1] * v2[1];

  // Compute barycentric coordinates
  const invDenom = 1 / (dot00 * dot11 - dot01 * dot01);
  const u = (dot11 * dot02 - dot01 * dot12) * invDenom;
  const v = (dot00 * dot12 - dot01 * dot02) * invDenom;

  // Check if the point is inside the triangle
  return u >= 0 && v >= 0 && u + v < 1;
}

//The starting y coord when the triangles are relocated ()
let initialYOffset = 0;
cursorFollowingDot = new Dot();
let selectedTriangle = null; // null indicates no triangle is selected yet.
let throttle_steering_json = {}; // Hold the current value for steering and throttle to be sent through the websocket
const midScreen = window.innerHeight / 2 + initialYOffset;

/**
 * Prints x,y and distance from the tip of the triangle to the current place of the ball.
 * @param {number} x current position of the ball (same as touch)
 * @param {*} y current position for the ball (same as touch)
 */
function calculateDistancePercentage(x, y) {
  let distance_percentage;

  // Calculate the differences in x and y coordinates to get coordinates relative to the tip
  const relativeX = x - window.innerWidth / 2;
  const relativeY = y - midScreen;

  if (y < midScreen) {
    distance_percentage = ((midScreen - y) / topTriangle.height) * 100;
    PrintStatistics(distance_percentage, relativeX, relativeY);
  } else {
    distance_percentage = ((y - midScreen) / bottomTriangle.height) * 100;
    PrintStatistics(distance_percentage, relativeX, relativeY);
  }

  function PrintStatistics(speed, x, y) {
    let shapeHeight = window.innerHeight / 4; //It is the same value as in updateDimensions()=> this.height

    // console.log("Throttle:", -((y - initialYOffset) / (window.innerHeight / 4)).toFixed(3),
    //   "Steering:", Number((x / (shapeHeight / Math.sqrt(3))).toFixed(3)));

    throttle_steering_json = {
      throttle: -((y - initialYOffset) / (window.innerHeight / 4)).toFixed(3),
      steering: Number((x / (shapeHeight / Math.sqrt(3))).toFixed(3)),
      button_b: 1,
    };
  }
}

/**
 * Set the value for the dot on the screen, and limit the movement to be inside the triangle the user touched first
 * @param {number} x position of the touch
 * @param {number} y position of the touch
 */
function handleDotMove(touchX, touchY) {
  // the triangles are divided by a mid-point. It can be referred to as the tip (the 10 px gap)
  const midScreen = window.innerHeight / 2 + initialYOffset;

  let minY, maxY, triangle;

  /*
relativeY variable represents the fraction of the distance the dot is from the tip of the triangle it is inside.
maxXDeviation is used to limit the movement of the ball

if condition is used to decide which triangle is the dot currently inside of it now
If the dot's y coordinate is less than the mid-point, then it's inside the top triangle. Otherwise, it's inside the bottom triangle.
*/

  if (selectedTriangle === 'top') {
    minY = midScreen - topTriangle.height;
    maxY = midScreen;
    triangle = topTriangle;
  } else if (selectedTriangle === 'bottom') {
    minY = midScreen;
    maxY = midScreen + bottomTriangle.height;
    triangle = bottomTriangle;
  }
  let triangleMidX = triangle.baseWidth / 2
  y = Math.max(minY, Math.min(touchY, maxY));
  const relativeY = (y - midScreen) / triangle.height;
  const maxXDeviation = Math.abs(relativeY) * (triangleMidX);
  x = Math.max(Math.min(touchX, (window.innerWidth / 2) + triangleMidX), (window.innerWidth / 2) - triangleMidX);

  //X value to limit the movement of the ball, while the calculated one is the x variable
  xOfDot = Math.max(Math.min(touchX, window.innerWidth / 2 + maxXDeviation), window.innerWidth / 2 - maxXDeviation);

  cursorFollowingDot.setPosition(xOfDot, y);
  calculateDistancePercentage(x, y);
}

const app = new PIXI.Application({
  width: window.innerWidth,
  height: window.innerHeight - 20,
  backgroundColor: 0xffffff,
  sharedTicker: true,
});

// Add a 10px margin to the top and bottom of the canvas
app.view.style.marginTop = '10px';
app.view.style.marginBottom = '10px';
document.body.appendChild(app.view);

//Creating the two triangles
const topTriangle = new Triangle('up');
const bottomTriangle = new Triangle('down', 'Backwards');

//Then add them to the canvas 9it is called stage in PiXi)
app.stage.addChild(topTriangle.graphics);
app.stage.addChild(bottomTriangle.graphics);

function redraw(yOffset = 0) {
  app.stage.removeChildren();
  topTriangle.drawTriangle(yOffset);
  bottomTriangle.drawTriangle(yOffset);
  app.stage.addChild(topTriangle.graphics);
  app.stage.addChild(bottomTriangle.graphics);

  // Always add cursorFollowingDot to the stage since it's instantiated at the beginning
  app.stage.addChild(cursorFollowingDot.graphics);
}

window.addEventListener('resize', () => {
  app.renderer.resize(window.innerWidth, window.innerHeight);
  topTriangle.updateDimensions();
  bottomTriangle.updateDimensions();
  redraw();
});

function handleTriangleMove(y) {
  const midScreen = window.innerHeight / 2;
  let yOffset = y - midScreen;

  const maxOffset = midScreen + topTriangle.height; // Maximum offset for the top triangle
  const minOffset = midScreen + bottomTriangle.height; // Minimum offset for the bottom triangle

  // Clamping the yOffset value to stop the triangles from crossing the screen's border
  if (yOffset > 0) {
    yOffset = Math.min(yOffset, minOffset - midScreen);
  } else {
    yOffset = Math.max(yOffset, -(maxOffset - midScreen));
  }

  redraw(yOffset);
}
/**
 * Second way to limit the user's interactions to be only inside the two triangles (first one is the if condition in handleTriangleMove() to limit the borders of the triangles)
 * @param {number} x the x-value for the position of touch
 * @param {number} y The y-value for the position of touch
 * @returns If the touch was in any of the two triangles, or even out
 */
function detectTriangle(x, y) {
  //Lots of spread syntax/ destructuring for the values of vertices in triangles
  if (pointInsideTriangle(x, y, ...topTriangle.vertices[0], ...topTriangle.vertices[1], ...topTriangle.vertices[2])) {
    return 'top';
  } else if (pointInsideTriangle(x, y, ...bottomTriangle.vertices[0], ...bottomTriangle.vertices[1], ...bottomTriangle.vertices[2])) {
    return 'bottom';
  } else {
    return 'none';
  }
}
let intervalId;
app.view.addEventListener('touchstart', (event) => {
  initialYOffset = event.touches[0].clientY - window.innerHeight / 2; // Calculate the initial Y offset
  const detectedTriangle = detectTriangle(event.touches[0].clientX, event.touches[0].clientY);
  //if condition  to make sure it will move only if the user clicks inside one of the two triangles
  if (detectedTriangle !== 'none') {
    selectedTriangle = detectedTriangle; // Set the selected triangle
    console.log('inside the triangles');

    // Create the dot
    cursorFollowingDot = new Dot();
    handleDotMove(event.touches[0].clientX, event.touches[0].clientY);
    app.stage.addChild(cursorFollowingDot.graphics);
    handleTriangleMove(event.touches[0].clientY);

    app.view.addEventListener('touchmove', onTouchMove);
    // Arrow function to send the command through websocket 
    intervalId = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(throttle_steering_json));
      } else {
        console.error('WebSocket is not open. Unable to send data.');
      }
      // The interval is high so it overcomes if a user is controlling from the normal UI with a controller (PS4)
    }, 1);
  }
});

app.view.addEventListener('touchend', () => {
  redraw(); // Reset triangles to their original position

  // Remove the dot
  if (cursorFollowingDot) {
    cursorFollowingDot.remove();
    cursorFollowingDot = null;
  }
  selectedTriangle = null; // Reset the selected triangle
  app.view.removeEventListener('touchmove', onTouchMove);
  throttle_steering_json = { steering: 0, throttle: 0 };
  clearInterval(intervalId);
});

function onTouchMove(event) {
  event.preventDefault(); // Prevent scrolling while moving the triangles

  // Update the dot's position
  if (cursorFollowingDot) {
    handleDotMove(event.touches[0].clientX, event.touches[0].clientY);
  }
}
