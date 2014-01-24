

ST.table = function() {

  function set_html(container_id)
  {
      return function(result, textStatus, jqXHR) {
          var container = $(ST.dialogs.jquery_id(container_id));
          container.html(result);
      };
  };

  function replace_item(container_id, item_value)
  {
      return function(result, textStatus, jqXHR) {
          var container = $(ST.dialogs.jquery_id(container_id));
          var button = container.find('table button[value="'+item_value+'"]');
          var row = button.closest('tr');
          if (result) {
              row.replaceWith(result);
          } else {
              button.parent().children().remove();
              row.fadeTo(200, 0.1);
          }
      };
  };

  function container_form_submit_data(container_id, url, data, method)
  {
      var container = $(ST.dialogs.jquery_id(container_id));
      var form = container.find('form');

      if (!method) method = "POST";

      var request = $.ajax({
          type: method,
          url: url,
          data: data
          });
      return request;
  };

  function container_form_submit(container_id, button, extra_data)
  {
      var container = $(ST.dialogs.jquery_id(container_id));
      var form = container.find('form');

      var data = form.serializeArray();

      if (button) {
          var element = $(button);
          data.push({
            name: element.attr('name'),
            value: element.attr('value')});
      }

      if (extra_data) {
          data.push.apply(data, extra_data);
      }

      return container_form_submit_data(
               container_id, form.attr('action'), data, 'POST');
  };

  function inc_counter(target, name, promise) {
      var counter = target.data(name);
      if (!counter) {
          counter = $.Deferred();
          counter.count = 0;
          target.data(name, counter);
          counter.done(function(){
              target.removeData(name);
          });
      }
      counter.count++;
      counter.notify(counter.count);
      promise.done( function(){
          counter.count--;
          counter.notify(counter.count);
          if (!counter.count) {
              counter.resolve();
          };
      });
      return counter;
  };

  function update_all_table_spinners(container_id) {
      var container = $(ST.dialogs.jquery_id(container_id));
      var actions = container.data('st-table-actions');
      if (actions !== undefined) {
          $.each(actions, function(button_value) {
                  show_button_spinner(container_id, button_value);
              });
      }
      update_table_spinner(container_id);
  }

  function register_table_action(target, button_value, promise) {
      var actions = target.data('st-table-actions');
      if (actions === undefined) {
          actions = {};
          target.data('st-table-actions', actions);
      }
      promise.done(function(){ delete actions[button_value]; });
      actions[button_value] = true;
  }

  function update_table_spinner(container_id) {
      var container = $(ST.dialogs.jquery_id(container_id));

      var counter = container.data('st-table-counter');
      var count = 0;
      if (counter)
          count = counter.count;

      var last_header = container.find('table.data>thead:first th:last');
      if (!last_header)
          return;

      var spinner_id = container_id+'-table-spinner';
      var spinner = last_header.find(ST.dialogs.jquery_id(spinner_id));
      if ((spinner.length>0) && (count<=0)) {
          spinner.remove();
      }
      if ((count>0) && (spinner.length==0)) {
          spinner = ST.images.spinner();
          spinner.addClass('st-table-spinner');
          spinner.attr('id', spinner_id);
          last_header.append(spinner);
      }
  }

  function show_table_spinner(container_id, request) {
      var container = $(ST.dialogs.jquery_id(container_id));
      var counter = inc_counter(container, 'st-table-counter', request);
      if (counter.count == 1) {
          // it's a new counter, register progress update
          counter.progress( function(count){
                  update_table_spinner(container_id);
          });
      }

  }

  function show_button_spinner(container_id, button_value) {
      var container = $(ST.dialogs.jquery_id(container_id));
      var button = container.find('table button[value="'+button_value+'"]');
      if (!button.length)
          return;
      button.hide();
      var spinner = ST.images.spinner();
      spinner.css('class', 'st-table-button-spinner');
      button.parent().append(spinner);
  }

  return {
      on_form_submit: function(container_id, button, extra_data) {
          var request = container_form_submit(container_id, button, extra_data);
          request.success(set_html(container_id));
          request.success(function(){ update_all_table_spinners(container_id); });
          show_table_spinner(container_id, request);
          return false;
      },

      on_form_submit_modal: function(container_id, button, extra_data,
                                     url, dialog_container_id, title)
      {
          var container = $(ST.dialogs.jquery_id(container_id));
          var form = container.find('form');
          var data = form.serializeArray();
          if (button) {
              var element = $(button);
              data.push({
                  name: element.attr('name'),
                  value: element.attr('value')});
          }

          if (extra_data) {
              data.push.apply(data, extra_data);
          }

          if (!dialog_container_id) {
              dialog_container_id = 'submit-modal-form';
          }
          ST.dialogs.open_modal_form(url, dialog_container_id, title, data);
          return false;
      },

      on_item_submit: function(container_id, button, extra_data) {
          var element = $(button);
          var item_value = element.attr('value');
          show_button_spinner(container_id, item_value);
          var request = container_form_submit(container_id, button, extra_data);

          var container = $(ST.dialogs.jquery_id(container_id));
          register_table_action(container, item_value, request);

          request.success(replace_item(container_id, item_value));
          show_table_spinner(container_id, request);
          return false;
      },

      on_form_sort: function(container_id, column_name, sort_on_name) {
          var field = $(ST.dialogs.jquery_id(sort_on_name));
          if (field.val()) {
              field.val(field.val() + ' ' + column_name);
          } else {
              field.val(column_name);
          };

          var request = container_form_submit(container_id);
          request.success(set_html(container_id));
          request.success(function(){ update_all_table_spinners(container_id); });
          show_table_spinner(container_id, request);

          return false;
      },

      on_standalone_sort: function(container_id, column_name, sort_on_name) {
          var container = $(ST.dialogs.jquery_id(container_id));
          var sort_names = container.data('ST.table.sort_key');
          if (sort_names) {
              sort_names.push(column_name);
          } else {
              sort_names = [column_name];
          }
          container.data('ST.table.sort_key', sort_names);

          var data = new Array();
          for (var i = 0, ie = sort_names.length; i < ie; i++) {
              data.push({
                      name: sort_on_name+':list',
                      value: sort_names[i]
                      });
          }

          var request = container_form_submit_data(container_id, data);
          request.success(set_html(container_id));
          request.success(function(){ update_all_table_spinners(container_id); });
          return false;
      },

      on_batch_link: function(container_id, postfix, start, size) {
          var data = new Array();
          data.push({
              name: 'start'+postfix,
              value: start
              });
          data.push({
              name: 'size'+postfix,
              value: size
              });
          var request = container_form_submit(container_id, null, data);
          request.success(set_html(container_id));
          request.success(function(){ update_all_table_spinners(container_id); });
          show_table_spinner(container_id, request);
          return false;
      },

      check_children: function(element) {
          var value = $(element).attr('checked');
          if (!value) {
              value = null;
          }
          var elements = $(element).closest('table').find('tbody input[type="checkbox"]')
          elements.attr('checked', value);
          return true;
      },

      select_all: function(event) {
          var element = event.target;
          $(element).closest('form').find('tbody input[type="checkbox"]').attr('checked', true);
          event.preventDefault();
      },

      select_none: function(event) {
          var element = event.target;
          $(element).closest('form').find('tbody input[type="checkbox"]').attr('checked', false);
          event.preventDefault();
      }

  };

}();
