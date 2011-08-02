/**
*
* SchoolTool - common information systems platform for school administration
* Copyright (c) 2011 Shuttleworth Foundation
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*
*/


ST = new Object();

/* ST local state extension */

ST.local = {};

ST.state = function() {
  /* "private" */
  var states = new Array();

  /* "public" */
  return {
    push: function() { states.push(ST.local); ST.local={}; },
    pop: function(){ ST.local = states.pop(); }
  }
}();

ST.redirect = function(destination) {
    if (destination) {
        window.location.replace(destination);
    }
}


/* ST common jquery dialogs */

ST.dialogs = function() {

  /* "private" */

  function before_dialog_load(selector) {
      // Fade out and/or add spinner or something here
      $(selector).empty();
  }

  function after_dialog_load(selector) {
  }

  function close_modal_form_dialog(selector) {
      // Fade out and/or add spinner or something here
      var dialog = $(selector);
      dialog.dialog("close");
      dialog.empty();
  }

  function modal_form_dialog(form_url, container_sel, title) {
      before_dialog_load(container_sel);
      var container = $(container_sel);
      var request = $.ajax({
              type: "GET",
              url: form_url,
          }).success(function(result, textStatus, jqXHR){
                  after_dialog_load(container);
                  handle_dialog_response(container, result, jqXHR);
                  if (title) {
                      container.dialog({title: title});
                  }
              });
  }

  function find_dialog(selector)
  {
      return $(selector).closest(".ui-dialog-content");
  }

  function handle_dialog_response(container, data, jqXHR) {
      var ct = jqXHR.getResponseHeader('content-type')||"";
      if (ct.indexOf('text/html') > -1) {
          container.html(data);
      } else if (ct.indexOf('application/json') > -1) {
          if (data['html']) {
              container.html(data['html']);
              container.hide();
          };
          if (data['dialog']) {
              container.dialog(data['dialog']);
          }
          if (data['redirect']) {
              ST.redirect(data['redirect']);
          };
      };
  }

  function ensure_container(container_id) {
      var container = $(jq_selector(container_id));
      if (container.length) {
          return container;
      }
      $('body').append('<div id="'+container_id+'"></div>');
      container = $('#'+container_id);
      return container;
  }

  function jq_selector(element_id)
  {
      return '#' + element_id.replace(/(:|\.)/g,'\\$1');
  }

  /* "public" */
  return {

    open_modal_link: function(link_sel)
    {
        var link = $(link_sel);
        var container_id = link.attr('id') + "-container";
        var container = ensure_container(container_id);
        var url = link.attr('href');
        modal_form_dialog(url, container);
        return false;
    },

    modal_form: function(link_id, form_url, container_id, title)
    {
        $(document).ready(function() {
                var link_sel = jq_selector(link_id);
                var container_sel = jq_selector(container_id);
                $(link_sel).attr("href", "#");
                $(link_sel).click(function(e) {
                        modal_form_dialog(form_url, container_sel, title);
                        e.preventDefault();
                    });
            });
    },

    find: find_dialog,

    submit: function(form_sel, button_sel)
    {
        var container = find_dialog(form_sel);
        var form = $(form_sel).closest('form');

        data = form.serializeArray();

        if (button_sel) {
            var button = $(button_sel);
            data.push({
                name: button.attr('name'),
                value: button.attr('value')});
        }

        before_dialog_load(container);

        var request = $.ajax({
            type: "POST",
            url: form.attr('action'),
            data: data,
            }).success(function(result, textStatus, jqXHR){
                after_dialog_load(container);
                handle_dialog_response(container, result, jqXHR);
                });

        return false;
    },

    close: function(form_sel)
    {
        var dialog = find_dialog(form_sel);
        close_modal_form_dialog(dialog);
        return false;
    },

  }

}();
