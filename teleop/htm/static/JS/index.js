function run_draw_map_python() {
    fetch('/run_draw_map_python')
        .then(response => response.json())
        //'map_date_href' is the returned data from 'run_draw_map_python' endpoint in server.py
        // it contains the date and the related path of the map .html 
        .then(map_date_href => {
            console.log(map_date_href)
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '';
            for (var map_date in map_date_href) {
                const listItem = document.createElement('li');
                const link = document.createElement('a');
                link.href = map_date_href[map_date];
                link.target = '_blank';
                link.textContent = map_date;
                listItem.appendChild(link);
                fileList.appendChild(listItem);
                // console.log( map_date, map_date_href[map_date] );
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
};

// Set the name of the hidden property and the change event for visibility
var hidden, visibilityChange;
if (typeof document.hidden !== "undefined") { // Opera 12.10 and Firefox 18 and later support
    hidden = "hidden";
    visibilityChange = "visibilitychange";
} else if (typeof document.msHidden !== "undefined") {
    hidden = "msHidden";
    visibilityChange = "msvisibilitychange";
} else if (typeof document.webkitHidden !== "undefined") {
    hidden = "webkitHidden";
    visibilityChange = "webkitvisibilitychange";
}

function start_all_handlers() {
    navigator_start_all();
    teleop_start_all();
    mjpeg_start_all();
    h264_start_all();
}

function stop_all_handlers() {
    navigator_stop_all();
    teleop_stop_all();
    mjpeg_stop_all();
    h264_stop_all();
}

function handleVisibilityChange() {
    if (document[hidden]) {
        stop_all_handlers();
    } else {
        start_all_handlers();
    }
}

$(function () {
    if (!dev_tools.is_develop()) {
        window.history.pushState({}, 'application_index_loaded', '/');
    }
    document.addEventListener(visibilityChange, handleVisibilityChange, false);
    window.addEventListener('focus', start_all_handlers);
    window.addEventListener('blur', stop_all_handlers);
    start_all_handlers();
});