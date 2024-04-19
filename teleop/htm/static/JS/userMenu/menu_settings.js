class RealSettingsBackend {
  constructor() {
  }
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


class FakeSettingsBackend extends RealSettingsBackend {
  constructor() {
    super();
  }
  _call_get_state(cb) {
    cb({ "platform": { 'entry': [new Date().toLocaleString()] } });
  }
  _call_get_settings(cb) {
    cb({ "vehicle": { "ras.driver.motor.scale": "14", "ras.driver.steering.offset": "0.54" } });
  }
  _call_save_settings(data, cb) {
    console.log("Dev backend save settings: " + data);
    cb({});
  }
}


var menu_settings = {
  _backend: null,

  _init: function (el_parent) {
    // In development mode there is no use of a backend.
    this._backend = dev_tools.is_develop() ? new FakeSettingsBackend() : new RealSettingsBackend();
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

  _poll_system_state: function () {
    menu_settings._backend._call_get_state(menu_settings._system_state_update);
  },

  _create_user_settings: function () {
    menu_settings._backend._call_get_settings(menu_settings._create_settings_form);
  },

  _start_state_polling: function () {
    setTimeout(menu_settings._poll_system_state, 0);
    setTimeout(menu_settings._poll_system_state, 2000);
    setTimeout(menu_settings._poll_system_state, 10000);
  },

  _settings_form_submit: function () {
    $("input#submit_save_apply").prop('disabled', true);
    const form_inputs = $("form#form_user_options").find(':input').toArray();
    let p_body = {};
  
    form_inputs.forEach((input) => {
      let isDirty = false;
      let value;
  
      // Check if the input is a checkbox and handle boolean values
      if (input.type === 'checkbox') {
        isDirty = input.checked.toString().toLowerCase() !== input.defaultValue.toLowerCase();
        value = input.checked ? 'True' : 'False'; // Convert boolean to string matching server expectation
      } else {
        isDirty = input.value !== input.defaultValue;
        value = input.value;
      }
  
      if (isDirty) {
        const section = input.attributes.section.value;
        p_body[section] = p_body[section] || [];
        p_body[section].push([input.name, value]);
      }
    });
  
    // p_body now contains the string 'True' or 'False' for checkboxes,
    // and the string value for other inputs. No need to map through p_body to convert values.
  
    menu_settings._backend._call_save_settings(JSON.stringify(p_body), function (data) {
      // Update the default values to the current state after successful save
      form_inputs.forEach((input) => {
        if (input.type === 'checkbox') {
          input.defaultValue = input.checked.toString(); // Update defaultValue to 'true' or 'false'
        } else {
          input.defaultValue = input.value;
        }
      });
      $("input#submit_save_apply").prop('disabled', false);
      menu_settings._start_state_polling();
    });
  },

  _create_settings_form: function (data) {
    const el_form = $("form#form_user_options");
    Object.keys(data).forEach(section => {
      var el_table = $("<table/>");
      el_table.append($("<caption/>").text(section).css('font-weight', 'bold').css('text-align', 'left'));
      var section_a = Object.keys(data[section]).sort();
      section_a.forEach(name => {
        var value = data[section][name].toString().toLowerCase(); // Convert to string and lower case for comparison
        var el_row = $("<tr/>");
        el_row.append($("<td/>").text(name));
        var el_input_td = $("<td/>");

        // Check if the value is a boolean
        if (value === 'true' || value === 'false') {
          // Create a toggle switch
          var el_input = $("<input/>", {
            section: section,
            name: name,
            type: 'checkbox',
            checked: value === 'true' // Check if the value is 'true'
          });
          el_input_td.append(el_input);
        } else {
          // Use a text input for non-boolean values
          el_input_td.append($("<input/>", {
            section: section,
            name: name,
            type: 'text',
            value: value,
            size: 40,
            maxlen: 80
          }));
        }
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

function menu_user_settings_main(el_parent) {
  menu_settings._init(el_parent);
}