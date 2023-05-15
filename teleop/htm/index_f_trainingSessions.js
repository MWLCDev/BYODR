window.onload = function () {
    var a = document.getElementById("open_training_sessions_list");
    var popup = document.getElementById("popupWindow");
    a.onclick = function () {
        // alert("I am an alert box!");
        // Show the pop-up window
        popup.style.display = "block";
        return false;
    }
}


function hidePopup() {
    // Get the pop-up window element
    var popup = document.getElementById("popupWindow");

    // Hide the pop-up window
    popup.style.display = "none";
}