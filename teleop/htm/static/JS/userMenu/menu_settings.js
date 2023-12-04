/**
 * Call Tornado backend to get system data and read the user options file (config.ini).
 * Save the user settings in config.ini after the user clicks save
 */
class RealSettingsBackend {
  constructor() {
  }
  // The cb function is a callback that gets executed after receiving the response from the server. It allows the code to wait for the asynchronous operation to complete and then process the result.
  _call_get_state(cb) {
    $.get("/teleop/system/state", cb);
  }
  _call_get_settings(cb) {
    $.get("/teleop/user/options", cb);
  }
  _call_save_settings(data, cb) {
    $.post("/teleop/user/options", data).done(cb);
  }
}

var menu_settings = {
  _backend: null,
  _init: function (el_parent) {
    this._backend = new RealSettingsBackend();
    // Construct the dom elements.
    const div_column = $("<div/>", { id: 'column' });
    div_column.append($("<h2/>").text("systems"));
    div_column.append($("<div/>", { id: 'system_state' }));
    div_column.append($("<h2/>").text("options"));
    div_column.append($("<form/>", { id: 'form_user_options', action: '' }));
    el_parent.append(div_column);
    // Get and render.
    this._poll_system_state();
    this._create_user_settings();
  },

  _poll_system_state: function () {
    menu_settings._backend._call_get_state(menu_settings._system_state_update);
  },

  _create_user_settings: function () {
    menu_settings._backend._call_get_settings(menu_settings._create_settings_form);
  },

  /**
   * Request data from a server immediately. after 2s and 10s.
   * It is called when the user saves so it updates the fields in the form.
   */
  _start_state_polling: function () {
    setTimeout(menu_settings._poll_system_state, 0);
    setTimeout(menu_settings._poll_system_state, 2000);
    setTimeout(menu_settings._poll_system_state, 10000);
  },

  /**
   * Handles the submission of the settings form. 
   * It disables the submit button, checks for changed values, prepares the data, and sends it to the server using _backend._call_save_settings. 
   * After saving, it restarts the state polling.
   */
  _settings_form_submit: function () {
    $("input#submit_save_apply").prop('disabled', true);
    const dirty_inputs = $("form#form_user_options").find(':input').toArray().filter(x => {
      return x.value != x.defaultValue
    });
    p_body = {};
    dirty_inputs.forEach((x, index, arr) => {
      const section = x.attributes.section.value;
      if (!p_body[section]) {
        p_body[section] = [];
      }
      p_body[section].push([x.name, x.value]);
    });
    menu_settings._backend._call_save_settings(JSON.stringify(p_body), function (data) {
      $("form#form_user_options").find(':input').toArray().forEach(el => { el.defaultValue = el.value; });
      menu_settings._start_state_polling();
    });
  },

  /**
   * Updates the system state display in the UI using the provided data.
   */
  _system_state_update: function (data) {
    const el_parent = $("div#system_state");
    el_parent.find('table').remove();
    var el_table = $("<table/>");
    Object.keys(data).forEach(subsystem => {
      Object.keys(data[subsystem]).forEach(timestamp => {
        var startup_errors = data[subsystem][timestamp];
        startup_errors.forEach(err_msg => {
          var el_row = $("<tr/>");
          el_row.append($("<td/>").text(subsystem));
          el_row.append($("<td/>").text(timestamp));
          el_row.append($("<td/>").text(err_msg));
          el_table.append(el_row);
        });
      });
    });
    el_parent.append(el_table);
  },

  /**
   * Creates the settings form based on the data received. 
   * It dynamically generates input fields for each setting, sets up the save button, and attaches an event listener for form changes.
   */
  _create_settings_form: function (data) {

    const el_form = $("form#form_user_options");
    Object.keys(data).forEach(section => {
      var el_table = $("<table/>");
      el_table.append($("<caption/>").text(section).css('font-weight', 'bold').css('text-align', 'left'));
      var section_a = Object.keys(data[section]).sort();
      section_a.forEach(name => {
        //This data is from ConfigManager function in server.py
        var value = data[section][name];
        var el_row = $("<tr/>");
        el_row.append($("<td/>").text(name));
        // Setup the input field for the option value.
        var el_input_td = $("<td/>")
        el_input_td.append($("<input/>", {
          section: section,
          name: name,
          type: 'text',
          value: value,
          size: 40,
          maxlen: 80
        }));
        el_row.append(el_input_td);
        el_table.append(el_row);
      });
      el_form.append(el_table);
    });
    const el_button = $("<input/>", {
      id: 'submit_save_apply',
      type: 'button',
      value: 'Save',
      disabled: true,
      click: menu_settings._settings_form_submit
    });
    el_form.append(el_button);
    el_form.on("input", function (evt) {
      el_button.prop('disabled', false);
    });
  }
}



// --------------------------------------------------- Init and public --------------------------------------------------------- //
/**
 * Entry point for initializing the settings menu.
 * Initialize the settings menu in the specified parent element.
 * @param {*} el_parent 
 */
function menu_user_settings_main(el_parent) {
  menu_settings._init(el_parent);
}