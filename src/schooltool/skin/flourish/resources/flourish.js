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
  function modal_form_dialog(form_url, form_id, title) {
      // Fade out and/or add spinner or something here
      $(form_id).empty();
      $(form_id).load(form_url, function(){
              $(form_id).dialog({
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

  /* "public" */
  return {

    modal_form: function(link_id, form_url, form_id, title)
    {
        $(link_id).attr("href", "#");
        $(document).ready(function(){
                $(link_id).click(function(e) {
                        modal_form_dialog(form_url, form_id, title);
                        e.preventDefault();
                    });
            });
    },

  }

}();
