import { topTriangle, bottomTriangle } from "/JS/mobileController/mobileController_b_shape_triangle.js"
import CTRL_STAT from '/JS/mobileController/mobileController_z_state.js';

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
  app.stage.addChild(CTRL_STAT.cursorFollowingDot.graphics);
}

export { app, redraw }