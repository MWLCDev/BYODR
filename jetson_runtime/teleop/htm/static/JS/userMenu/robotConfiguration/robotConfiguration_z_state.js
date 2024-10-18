class RobotState {
  // Data in segments table
  #segmentsData = []
  //Save the raw data from the robot_config.ini
  #robotConfigData = []


  set segmentsData(newSegments) {
    // Calculate the length of old and new data
    const oldLength = Object.keys(this.#segmentsData).length;
    const newLength = Object.keys(newSegments).length;
    // If new data has additional segments
    if (newLength > oldLength) {
      // Identify the new segments only
      const newSegmentKeys = Object.keys(newSegments).slice(oldLength);
      // Check each new segment for duplicates in the existing data
      for (const key of newSegmentKeys) {
        const newSegment = newSegments[key];
        let isDuplicate = false;
        for (const existingKey in this.#segmentsData) {
          if (this.#segmentsData.hasOwnProperty(existingKey)) {
            const existingSegment = this.#segmentsData[existingKey];
            if (existingSegment['wifi.name'] === newSegment['wifi.name'] &&
              existingSegment['mac.address'] === newSegment['mac.address']) {
              console.log(`${newSegment['wifi.name']} network is already added.`);
              isDuplicate = true;
              break;
            }
          }
        }

        // If any new segment is a duplicate, retain the old data and return
        if (isDuplicate) {
          return;
        }
      }

      // If there are no duplicates, update #segmentData with the new data
      this.#segmentsData = newSegments;
    }
  }

  get segmentsData() {
    return this.#segmentsData;
  }

  set robotConfigData(value) {
    this.#robotConfigData = value
  }
  get robotConfigData() {
    return this.#robotConfigData
  }

}

const sharedState = new RobotState();

// Shared instance will make sure that all the imports can access the same value without change in them
export default sharedState;
