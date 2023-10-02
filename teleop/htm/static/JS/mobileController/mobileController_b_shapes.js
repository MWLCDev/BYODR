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
//Creating the two triangles
const topTriangle = new Triangle('up');
const bottomTriangle = new Triangle('down', 'Backwards');

export { topTriangle, bottomTriangle, Triangle, Dot };