class Rectangle
{
  constructor(position)
  {
    this.position = position; // The position of the rectangle in the screen => 'top' or 'bottom'
    this.height = (window.innerHeight/2); // The height of the rectangle. its height is half of the screen
    this.width = window.innerWidth; // The width of the rectangle. Its the entire width of the screen
    this.container = new PIXI.Container(); // The "canvas" onto which the rectangle will be drawn
    this.graphics = new PIXI.Graphics(); // The "painting" that will go on the canvas, the rectangle

    // Initiator methods of the class
    this.container.addChild(this.graphics);
    this.drawText();
  }
  
  static headerTextStyle = new PIXI.TextStyle
  ({
    fontSize: 28,
    fill: 'white',
    align: 'center',
  });

  // Method that adds the text in the rectangle
  drawText()
  {

    // If we are drawing the top rectangle
    if (this.position === 'top')
    {
      this.textObj = new PIXI.Text('ɅɅɅ - STOP - ɅɅɅ', Rectangle.headerTextStyle); // Text that appears on the top rectangle
      this.textObj.anchor.set(0.5, 1); // Horizontally center and vertically bottom
      this.textObj.position.set(this.width/2, this.height); // Position at the center and bottom of the top rectangle
    }

    // If we are drawing the bottom rectangle
    else if (this.position === 'bottom')
    {
      this.textObj = new PIXI.Text('VVV - STOP - VVV', Rectangle.headerTextStyle); // Text that appears on the bottom rectangle
      this.textObj.anchor.set(0.5, 0); // Horizontally center and vertically top
      this.textObj.position.set(this.width/2, this.height); // Position at the center and top of the bottom rectangle
    }

    this.drawRectangle();  // Redraw to adjust position based on new text.
    this.graphics.addChild(this.textObj); // Add text to the rectangle
  }

  // Method that draws the rectangle on the local container
  drawRectangle()
  {
    this.graphics.clear();
    this.graphics.beginFill(0xff0000); // Red color


    // drawRect() arguments: X coords of the TL point, Y coords of the TL point, width, height
    if (this.position === 'top') // The top rectangle
      // The top left point of the top rectangle touches the top left corner of the screen => (0,0)
      this.graphics.drawRect(0, 0, this.width, this.height);
    
    else
      // The top left point of the top rectangle touches the left side of the screen, half of the screen down
      this.graphics.drawRect(0, this.height, this.width, this.height);
    
    this.graphics.endFill();
  }
}

const topRectangle = new Rectangle('top');
const bottomRectangle = new Rectangle('bottom');

export { topRectangle, bottomRectangle };