function run_draw_map_python() {
  fetch("/run_draw_map_python")
    .then((response) => response.json())
    .then((map_date_href) => {
      // console.log(map_date_href);
      const fileList = document.getElementById("fileList");
      fileList.innerHTML = "";
      for (var map_date in map_date_href) {
        const listItem = document.createElement("li");
        const link = document.createElement("a");
        link.href = map_date_href[map_date];
        link.target = "_blank";
        link.textContent = map_date;
        listItem.appendChild(link);
        fileList.appendChild(listItem);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}
window.onload = function () {
  var a = document.getElementById("open_training_sessions_list");
  var popup = document.getElementById("popupWindow");
  a.onclick = function () {
    popup.style.display = "block";
    return false;
  };
};

function hidePopup() {
  var popup = document.getElementById("popupWindow");
  popup.style.display = "none";
  const fileList = document.getElementById("fileList");
  fileList.innerHTML = ""; // Clear existing file list
}
