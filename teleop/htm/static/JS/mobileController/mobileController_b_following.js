const toggleButton = document.getElementById('toggleButton');

toggleButton.addEventListener('click', function () {
  const command = toggleButton.innerText === "Start Following" ? "Stop Following" : "Start Following";

  // Toggle button text and color
  toggleButton.innerText = command;
  toggleButton.style.backgroundColor = command === "Stop Following" ? "#ff6347" : "#67b96a";

  fetch('/switch_following', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: `command=${encodeURIComponent(command)}`,
  })
    .then(response => response.json())
    .then(data => console.log("Server response:", data))
    .catch(error => console.error("Error sending command:", error));
});

