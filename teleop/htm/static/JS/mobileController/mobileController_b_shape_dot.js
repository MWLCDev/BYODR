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

  hide() {
    this.graphics.alpha = 0;
  }

  show() {
    this.graphics.alpha = 1;
  }
}

export { Dot };
