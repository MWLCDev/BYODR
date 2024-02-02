// Add event listener to toggle button
toggleButton.addEventListener('click', function() {
    // Toggle functionality here
    console.log(toggleButton.classList.contains('toggled'))
    if (toggleButton.classList.contains('toggled')==false){
      toggleButton.classList.toggle('toggled')
      toggleButton.innerText = 'Stop following'
      toggleButton.style.backgroundColor = '#e06e6e'
    }
    else if (toggleButton.classList.contains('toggled')==true){
      toggleButton.classList.toggle('toggled')
      toggleButton.innerText = 'Start following'
      toggleButton.style.backgroundColor = '#67b96a'
      var test = 0;
    }
});

function initializeFollowingWS(){

}

function sendJSONFollowing(){

}

export {initializeFollowingWS, sendJSONFollowing}