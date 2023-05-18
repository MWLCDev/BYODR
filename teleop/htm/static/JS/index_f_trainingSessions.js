window.onload = function () {
    var a = document.getElementById("open_training_sessions_list");
    var popup = document.getElementById("popupWindow");
    a.onclick = function () {
        popup.style.display = "block";
        return false;
    }
}

function hidePopup() {
    var popup = document.getElementById("popupWindow");
    popup.style.display = "none";
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = ''; // Clear existing file list
}