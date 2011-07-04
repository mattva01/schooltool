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

  function modal_form_dialog(form_url, form_sel, title) {
      before_dialog_load(form_sel);
      $(form_sel).load(form_url, function(){
              after_dialog_load(form_sel);
              $(form_sel).dialog({
                  autoOpen: true,
                  modal: true,
                  resizable: false,
                  draggable: false,
                  position: ['center','middle'],
                  width: 'auto',
                  title: title
                  })
          });
  }

  function find_dialog(selector)
  {
      return $(selector).closest(".ui-dialog-content");
  }

  /* "public" */
  return {

    modal_form: function(link_sel, form_url, form_sel, title)
    {
        $(link_sel).attr("href", "#");
        $(document).ready(function(){
                $(link_sel).click(function(e) {
                        modal_form_dialog(form_url, form_sel, title);
                        e.preventDefault();
                    });
            });
    },

    find: find_dialog,

    submit: function(form_sel, button_sel)
    {
        var dialog = find_dialog(form_sel);
        var form = $(form_sel).closest('form');

        data = form.serializeArray();

        if (button_sel) {
            var button = $(button_sel);
            data.push({
                name: button.attr('name'),
                value: button.attr('value')});
        }

        before_dialog_load(dialog);

        $.ajax({
            type: "POST",
            url: form.attr('action'),
            data: data,
            success: function(result){
                after_dialog_load(dialog);
                dialog.html(result);
                // XXX: congratulations, we have just screwed up dialog witdth.
                }
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
