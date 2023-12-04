class AdminMenu {
  constructor(element) {
    this.element = element;
  }

  // Method to clear all child elements
  clearContents() {
    while (this.element.firstChild) {
      this.element.removeChild(this.element.firstChild);
    }
  }

  // Method to fetch data from the API and display it
  fetchDataAndDisplay() {
    fetch('/teleop/robot/options')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        this.clearContents();
        this.displayData(data);
      })
      .catch(error => {
        console.error('There has been a problem with your fetch operation:', error);
      });
  }

  // Method to display the data
  displayData(data) {
    // Create a div to show the data
    const dataDiv = document.createElement('div');
    dataDiv.textContent = JSON.stringify(data, null, 2);
    this.element.appendChild(dataDiv);
  }
}
