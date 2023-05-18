
const express = require('express');
const cors = require('cors');
const app = express();
const port = 3000;
const path = require('path');
const fs = require('fs').promises;


app.use(cors()); // Enable CORS for all routes

app.get('/api/training_sessions', async (req, res) => {
  try {
    const folderPath = path.join(__dirname, '../../plot_training_sessions_map/training_maps');
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
