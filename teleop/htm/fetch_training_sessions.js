const express = require('express');
const path = require('path');
const fs = require('fs').promises;

const app = express();
const port = 3000;

app.get('/files', async (req, res) => {
  try {
    const folderPath = path.join(__dirname, 'plot_training_sessions_map/training_maps');
    const files = await fs.readdir(folderPath);
    res.json(files);
  } catch (error) {
    console.error('Error:', error);
    res.status(500).send('Internal Server Error');
  }
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
