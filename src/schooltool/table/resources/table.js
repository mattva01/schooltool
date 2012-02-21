

ST.table = function() {

  function container_form_submit_data(container_id, data)
  {
      var container = $(ST.dialogs.jquery_id(container_id));
      var form = container.find('form');
      var request = $.ajax({
          type: "POST",
          url: form.attr('action'),
          data: data,
          }).success(function(result, textStatus, jqXHR){
              container.html(result);
              });
      return false;
  };

  function container_form_submit(container_id, button)
  {
      var container = $(ST.dialogs.jquery_id(container_id));
      var form = container.find('form');

      data = form.serializeArray();

      if (button) {
          var element = $(button);
          data.push({
            name: element.attr('name'),
            value: element.attr('value')});
      }

      return container_form_submit_data(container_id, data);
  };

  return {
      on_form_submit: container_form_submit,

      on_form_sort: function(container_id, column_name, sort_on_name) {
          var field = $(ST.dialogs.jquery_id(sort_on_name));
          if (field.val()) {
              field.val(field.val() + ' ' + column_name);
          } else {
              field.val(column_name);
          }
          return container_form_submit(container_id);
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
          return container_form_submit_data(container_id, data);
      },

  };

}();
