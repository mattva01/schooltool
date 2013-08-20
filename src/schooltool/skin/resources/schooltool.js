//
// SchoolTool - common information systems platform for school administration
// Copyright (c) 2003 Shuttleworth Foundation
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
//
// Javascript for Schoolbell calendar
//
// $Id$

//
// Generic PopUp window function for calendar forms
//
// Call with
// <a href="javascript:popUp('foo.html')" title="Pop Up Foo">
//   Popup Window
// </a>

function popUp(url) {
	window.open( url, "myWindow", "status = 1,	\
					toolbar=0,	\
					scrollbars=1,	\
					menubar=0,	\
					statusbar=0,	\
					height = 500,	\
					width = 650,	\
					resizable = 1" );
}

function jumpTo(box) {
	destination = box.form.jump.options[box.form.jump.selectedIndex].value;
	if (destination) location.href = destination;
}


// Tooltips for various calendar views

var x = 0;
var y = 0;
var tipon = false;
var tip = null;

function onBodyLoad() {
    document.captureEvents(Event.MOUSEMOVE);
    document.onmousemove = followMouse;
}

function followMouse(e) {
    x = e.pageX;
    y = e.pageY;
    if(tip){
        tip.style.top = (y + 10) + 'px';
        tip.style.left = (x + 10) + 'px';
    }
    return true;
}

function showToolTip(elem, id) {
    elem.style.borderColor = 'black';
    tip = document.getElementById(id);
    tip.style.visibility = 'visible';
    tip.style.position = 'absolute';
    tip.style.display = 'block';
}

function hideToolTip(elem) {
    tip.style.visibility = 'hidden';
    tip = null;
}



var justClicked = false;
// Set up event handling for action bar drop downs.
function initializeEventBindings(){

  $(document).click(function(){
    if (justClicked == false){
    $("div.dropdown")
      .removeClass("expanded")
      .addClass("contracted");
    } 
    else {
      justClicked = false;
    }
  });

  $("div.dropdown").each(function(i){
    $(this).click(function() { 
      $(this)
	.toggleClass("contracted")
	.toggleClass("expanded");
      justClicked = true;
    });
  });
}

$(document).ready(initializeEventBindings);
