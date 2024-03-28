
class Triangle {
  constructor(direction, text) {
    this.direction = direction;
    this.height = window.innerHeight / 4;
    this.baseWidth = 2 * (this.height / Math.sqrt(3));
    this.text = text;
    this.subText;
    this.container = new PIXI.Container();
    this.graphics = new PIXI.Graphics();
    this.currentSSID;
    this.container.addChild(this.graphics);
    this.updateDimensions();
    this.drawTriangle();
    if (text) {
      this.drawText(text);
    }

    if (this.direction === 'up') {
      if (!this.text) {
        this.getSSID();
      }
    }
  }


  async getSSID() {
    try {
      const response = await fetch('/run_get_SSID');
      this.currentSSID = await response.text();
      this.drawText(this.currentSSID); // Call function to redraw the text after it has being fetched
    } catch (error) {
      console.error("Error fetching SSID for current robot:", error);
    }
  }

  changeText(newText, fontSize = undefined) {
    if (newText === "controlError") {
      newText = "Control Lost";
      this.subText = "Refresh the Page";
    } else if (newText === "connectionError") {
      newText = "Connection Lost";
      this.subText = "Please reconnect";
    }
    if (this.textObj) {
      this.graphics.removeChild(this.textObj);
    }
    this.text = newText;
    this.drawText(newText, fontSize);
  }


  drawText(newText, fontSize) {
    const headerTextStyle = new PIXI.TextStyle({
      fontSize: fontSize || 28, // Use provided fontSize or default to 28
      fill: 'white',
      align: 'center',
    });

    this.textObj = new PIXI.Text(newText, headerTextStyle);

    // Remove previous subTextObj if it exists
    if (this.subTextObj) {
      this.graphics.removeChild(this.subTextObj);
    }

    // Check and draw subText
    if (this.direction === 'up' && this.subText) {
      const subTextStyle = new PIXI.TextStyle({
        fontSize: (fontSize ? fontSize * 0.5 : 15), // Example: smaller font size for subText
        fill: 'white',
        align: 'center',
      });
      this.subTextObj = new PIXI.Text(this.subText, subTextStyle);
      this.subTextObj.anchor.set(0.5, 0); // Horizontally center and vertically top
      this.graphics.addChild(this.subTextObj);
    }

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


  drawTriangle(yOffset = 0, color = 0x000000) {
    this.graphics.clear();
    this.graphics.beginFill(color); // Use this.color or default to black
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

      // Positioning the subText 10px below the header text
      if (this.subTextObj) {
        this.subTextObj.position.set(window.innerWidth / 2, this.textObj.position.y + this.textObj.height + 5);
      }
    } else {
      // Positioning the text above the base of the lower triangle
      this.textObj.position.set(window.innerWidth / 2, yOffset + midScreen + this.height);
    }
  }
}

const topTriangle = new Triangle('up');
const bottomTriangle = new Triangle('down', 'Backwards');

export { topTriangle, bottomTriangle };