
  // Handle radio button changes
  $('.channel input[type="radio"]').change(function () {
      const parent = $(this).closest('.channel');
      const channelIndex = parent.data('index') + 1;
      const value = $(this).val() === 'true';

      saveChannelState(channelIndex, value);
  });

  // Function to fetch and update relay states from the backend
  export function updateRelayStates() {
      $.get(`${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`, function (response) {
          const states = response['states'];
          $('.channel').each(function () {
              const index = $(this).data('index');
              const state = states[index] === true;
              $(this).find(`input[value="${state}"]`).prop('checked', true);
          });
      });
  }

  // Function to send the current state of a relay to the backend
  function saveChannelState(channel, value) {
      const command = { channel: channel, action: value ? 'on' : 'off' };
      $.post(
          `${window.location.protocol}//${window.location.hostname}:8082/teleop/pilot/controls/relay/state`,
          JSON.stringify(command),
          function (response) {
              // Optionally handle response
              updateRelayStates(); // Refresh states after change
          },
          'json'
      );
  }