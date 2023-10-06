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

class Triangle {
  constructor(direction, text) {
    this.direction = direction;
    this.height = window.innerHeight / 4;
    this.baseWidth = 2 * (this.height / Math.sqrt(3));
    this.text = text;
    this.container = new PIXI.Container();
    this.graphics = new PIXI.Graphics();
    this.container.addChild(this.graphics);
    this.updateDimensions();
    this.drawTriangle();
    if (text) {
      this.drawText(text);
    }

    if (this.direction === 'up') {
      this.getSSID();
    }
  }
  static textStyle = new PIXI.TextStyle({
    fill: 'white',
    fontSize: 20,
    align: 'center',
  });

  async getSSID() {
    try {
      const response = await fetch('/run_get_SSID');
      const data = await response.text();
      this.drawText(data); // Call function to redraw the text after it has being fetched
    } catch (error) {
      console.error("Error fetching SSID for current robot:", error);
    }
  }

  drawText(newText) {
    this.textObj = new PIXI.Text(newText, Triangle.textStyle);
    if (this.direction === 'up') {
      this.textObj.anchor.set(0.5, 0); // Horizontally center and vertically top
    } else {
      this.textObj.anchor.set(0.5, 1); // Horizontally center and vertically bottom
    }
    this.graphics.addChild(this.textObj);
    this.drawTriangle();  // Redraw to adjust position based on new text.
  }

  /**
   * Limit the width to be only a maximum of 600px (for mobile screens) 
   */
  updateDimensions() {
    if (this.baseWidth > 600) {
      this.baseWidth = 600;
      this.height = (this.baseWidth * Math.sqrt(3)) / 2;
    }
  }


  drawTriangle(yOffset = 0) {
    this.graphics.clear();
    this.graphics.beginFill(0x000000);
    const midScreen = window.innerHeight / 2;
    const yOffsetAdjustment = this.direction === 'up' ? -5 : 5;// Tip between the two triangle

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
    }
    if (this.textObj) {
      this.alignText(yOffset, midScreen, yOffsetAdjustment)
    }
    this.graphics.drawPolygon(this.vertices.flat());
    this.graphics.endFill();
  }

  alignText(yOffset, midScreen, yOffsetAdjustment) {
    if (this.direction === 'up') {
      // Positioning the text below the base of the upper triangle
      this.textObj.position.set(window.innerWidth / 2, yOffset + midScreen - this.height + yOffsetAdjustment + 5);
    } else {
      // Positioning the text above the base of the lower triangle
      this.textObj.position.set(window.innerWidth / 2, yOffset + midScreen + this.height);
    }
  }
}

// Create the two triangles
const topTriangle = new Triangle('up');
const bottomTriangle = new Triangle('down', 'Backwards');

export { topTriangle, bottomTriangle, Triangle, Dot };