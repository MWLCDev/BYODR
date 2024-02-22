const toggleButton = document.getElementById('toggleButton');

toggleButton.addEventListener('click', function () {
  const command = toggleButton.innerText === "Start Following" ? "Start Following" : "Stop Following";

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

      // Toggle button text and color
  toggleButton.innerText = command === "Start Following" ? "Stop Following" : "Start Following";
  toggleButton.style.backgroundColor = toggleButton.innerText === "Stop Following" ? "#ff6347" : "#67b96a";
});

export { toggleButton };