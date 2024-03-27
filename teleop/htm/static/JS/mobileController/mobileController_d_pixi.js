import { topTriangle, bottomTriangle } from "./mobileController_b_shape_triangle.js"
import { topRectangle, bottomRectangle } from "./mobileController_b_shape_red_rectangle.js"
import CTRL_STAT from './mobileController_z_state.js';

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

//Then add them to the canvas (it is called stage in PiXi)
app.stage.addChild(topTriangle.graphics);
app.stage.addChild(bottomTriangle.graphics);


function removeTriangles() {
  // Check if the top triangle's graphics are currently a child of the stage
  if (app.stage.children.includes(topTriangle.graphics)) {
    app.stage.removeChild(topTriangle.graphics);
  }

  // Check if the bottom triangle's graphics are currently a child of the stage
  if (app.stage.children.includes(bottomTriangle.graphics)) {
    app.stage.removeChild(bottomTriangle.graphics);
  }
}

function changeTrianglesColor(color) {
  topTriangle.drawTriangle(undefined, color);
  bottomTriangle.drawTriangle(undefined, color);
}

function redraw(drawOption = "both", yOffset = 0, resetText = false) {
  app.stage.removeChildren();

  if (drawOption === "top" || drawOption === "both") {
    topTriangle.drawTriangle(yOffset);
    app.stage.addChild(topTriangle.graphics);
  }

  if (drawOption === "bottom" || drawOption === "both") {
    bottomTriangle.drawTriangle(yOffset);
    app.stage.addChild(bottomTriangle.graphics);
  }

  if (resetText) {
    topTriangle.changeText(topTriangle.currentSSID)
    bottomTriangle.changeText("Backwards")
    redraw()
  }
  // Always add cursorFollowingDot to the stage since it's instantiated at the beginning
  if (CTRL_STAT.isWebSocketOpen)
    app.stage.addChild(CTRL_STAT.cursorFollowingDot.graphics);
}

function drawTopTriangle_BottomRectangle(yOffset = 0) {
  app.stage.removeChildren();
  topTriangle.drawTriangle(yOffset);
  app.stage.addChild(topTriangle.graphics);

  // Draw the red area at the bottom
  app.stage.addChild(bottomRectangle.graphics);

  // Always add cursorFollowingDot to the stage since it's instantiated at the beginning
  if (CTRL_STAT.isWebSocketOpen)
    app.stage.addChild(CTRL_STAT.cursorFollowingDot.graphics);
}

function drawBottomTriangle_TopRectangle(yOffset = 0) {
  app.stage.removeChildren();
  bottomTriangle.drawTriangle(yOffset);
  app.stage.addChild(bottomTriangle.graphics);

  // Draw the red area at the bottom
  app.stage.addChild(topRectangle.graphics);

  // Always add cursorFollowingDot to the stage since it's instantiated at the beginning
  if (CTRL_STAT.isWebSocketOpen)
    app.stage.addChild(CTRL_STAT.cursorFollowingDot.graphics);
}


export { app, changeTrianglesColor, redraw, removeTriangles, drawTopTriangle_BottomRectangle, drawBottomTriangle_TopRectangle }