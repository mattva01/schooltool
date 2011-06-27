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


/* Stuff to refactor */

$(document).ready(function() {
    // accordion setup
    $( ".person-info" ).accordion({
        header: 'h2',
        collapsible: true,
        autoHeight: false,
    });
});


function call_dialog(url, form_id) {
    $(form_id).load(url).hide();
    width = $(form_id).width() + 30;
    $(form_id).dialog({
        autoOpen: false,
        modal: true,
        resizable: false,
        draggable: false,
        width: width
    });
    $(form_id).dialog('open');
}


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
  function call_modal_form(form_url, form_id) {
      // Fade out and/or add spinner or something here
      $(form_id).empty();
      $(form_id).load(form_url, function(){
              var title_hack = $(form_id).find('h3').html();
              $(form_id).dialog({
                  autoOpen: true,
                  modal: true,
                  resizable: false,
                  draggable: false,
                  position: ['center','middle'],
                  width: 'auto',
                  title: title_hack
                  })
          });
  }

  /* "public" */
  return {

    modal_form: function(link_id, form_url, form_id)
    {
        $(document).ready(function(){
                $(link_id).click(function(e) {
                        call_modal_form(form_url, form_id);
                        e.preventDefault();
                    });
            });
    },

  }

}();
