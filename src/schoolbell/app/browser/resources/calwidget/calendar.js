/**
* Calendar Widget Version 1.0
* Copyright (c) 2004, Tribador Mediaworks,
*
* Brian Munroe <bmunroe@tribador.net>
*
* calendar.js - Calendar Widget JavaScript Library
*
* Permission to use, copy, modify, distribute, and sell this software and its
* documentation for any purpose is hereby granted without fee, provided that
* the above copyright notice appear in all copies and that both that
* copyright notice and this permission notice appear in supporting
* documentation.  No representations are made about the suitability of this
* software for any purpose.  It is provided "as is" without express or
* implied warranty.
*/

function pageOffsetLeft(elem) {

    if (elem.offsetParent) {
        for(var offX = 0; elem.offsetParent; elem = elem.offsetParent){
            offX += elem.offsetLeft;
        }

        return offX;
    } else {
        return elem.x;
    }
}

function pageOffsetTop(elem) {

    if (elem.offsetParent) {
        for(var offY = 0; elem.offsetParent; elem = elem.offsetParent){
            offY += elem.offsetTop;
        }
        return offY;
    } else {
        return elem.y;
    }
}

function _isLeapYear(year) {
    return (((year % 4 == 0) && (year % 100 != 0)) || (year % 400 == 0)) ? 1 : 0;
}

function setCalendar(idtag,yyyy,mm,dd) {
    y = document.getElementById(idtag);
    // Zero pad months and days
    if (mm < 10) {
        mm = "0" + mm;
    }
    if (dd < 10) {
        dd = "0" + dd;
    }
    y.value = yyyy + "-" + mm + "-" + dd;
    y = document.getElementById(idtag + "Div");
    y.style.display = "none";
}

function closeCal(idtag) {
    t = document.getElementById(idtag + "Div");
    t.style.display = "none";
}

function closeCalNoDate(idtag) {
    y = document.getElementById(idtag);
    y.value = "";
    t = document.getElementById(idtag + "Div");
    t.style.display = "none";
}

function closeCalSetToday(idtag) {
    var doDate = new Date();
    var mm = doDate.getMonth()+1;
    var dd = doDate.getDate();
    var yyyy = doDate.getYear();

    if (yyyy < 1000) {
        yyyy = yyyy + 1900;
    }

    setCalendar(idtag,yyyy,mm,dd);
}

function redrawCalendar(idtag) {

    var x = document.getElementById(idtag + "SelectMonth");
    for (i = 0; i < x.options.length;i++){
        if (x.options[i].selected) {
            var mm = x.options[i].value;
        }
    }

    var y = document.getElementById(idtag + "SelectYear");
    for (i = 0; i < y.options.length; i++) {
        if (y.options[i].selected) {
            var yyyy = y.options[i].value;
        }
    }

    // Who f-ing knows why you need this?
    // If you don't cast it to an int,
    // the browser goes into some kind of
    // infinite loop, atleast in IE6.0/Win32
    //
    mm = mm*1;
    yyyy = yyyy*1;

    drawCalendar(idtag,yyyy,mm);
}

function _buildCalendarControls() {

    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    var nw = new Date();

    (arguments[0] ? idtag = arguments[0] : idtag = "");
    (arguments[1] ? yyyy = arguments[1] : yyyy = nw.getYear());
    (arguments[2] ? mm = arguments[2] : mm = nw.getMonth());
    (arguments[3] ? dd = arguments[3] : dd = nw.getDay());

    // Mozilla hack,  I am sure there is a more elegent way, but I did it
    // on a Friday to get a release out the door...
    //
    if (yyyy < 1000) {
        yyyy = yyyy + 1900;
    }

    var monthArray = '<select class ="DateControls" id="' + idtag + 'SelectMonth" onChange="redrawCalendar(\'' + idtag + '\');">';
    // First build the month selection box
    for (i = 0; i < months.length; i++){
        if (i == mm-1) {
            monthArray = monthArray + '<option value="' + eval(i + 1) + '" selected="selected">' + months[i] + '</option>';
        } else {
            monthArray = monthArray + '<option value="' + eval(i + 1) + '">' + months[i] + '</option>';
        }
    }
    monthArray = monthArray + "</select>";

    var yearArray = '<select class ="DateControls" id="' + idtag + 'SelectYear" onChange="redrawCalendar(\'' + idtag + '\');">';
    for (i=yyyy-4;i<= yyyy+4;i++){
        if (i == yyyy) {
            yearArray = yearArray + '<option value="' + i + '" selected="selected">' + i + '</option>';
        } else {
            yearArray = yearArray + '<option value="' + i + '">' + i + '</option>';
        }
    }
    yearArray = yearArray + "</select>";
    return(monthArray + " " + yearArray);
}

function clickWidgetIcon(idtag) {
    (arguments[0] ? idtag = arguments[0] : idtag = "");

    t = document.getElementById(idtag + "Div");
    if (t.style.display == "none") {
        drawCalendar(idtag);
    } else {
        closeCal(idtag);
    }
}

function drawCalendar() {

    (arguments[0] ? idtag = arguments[0] : idtag = "");
    (arguments[1] ? yyyy = arguments[1] : yyyy = void(0));
    (arguments[2] ? mm = arguments[2] : mm = void(0));
    (arguments[3] ? dd = arguments[3] : dd = void(0));

    if (!yyyy && !mm) {
        x = document.getElementById(idtag);
        if (x.value != "") {
            var wholeValue = x.value;
            var dateparts = wholeValue.split("-");
            var yyyy = dateparts[0]*1;
            var mm = dateparts[1]*1;
            var dd = dateparts[2]*1;
        } else {
            var doDate = new Date();
            var mm = doDate.getMonth()+1;
            var dd = doDate.getDate();
            var yyyy = doDate.getYear();
        }
    }

    // Mozilla hack,  I am sure there is a more elegent way, but I did it
    // on a Friday to get a release out the door...
    if (yyyy < 1000) {
        yyyy = yyyy + 1900;
    }

    var newDate = new Date(yyyy,mm-1,1);
    var startDay = newDate.getDay();
    var dom = [31,28,31,30,31,30,31,31,30,31,30,31];
    var dateControls = '<tr><td class="DateControlFrame" colspan="7">' + _buildCalendarControls(idtag,yyyy,mm,dd) + '</td></tr>';
    var beginTable = '<table class="CalendarFrame">';
    var calHeader = '<tr><td class="CalHeader">Su</td><td class="CalHeader">Mo</td><td class="CalHeader">Tu</td><td class="CalHeader">We</td><td class="CalHeader">Th</td><td class="CalHeader">Fr</td><td class="CalHeader">Sa</td></tr>';
    var closeControls = '<tr><td class="CloseControls" colspan="7"> <a class="close" onclick="closeCal(\'' + idtag + '\');">Close</a>  &nbsp;&nbsp;&nbsp; <a class="cancel" onclick="closeCalNoDate(\'' + idtag + '\');">No Date</a> &nbsp;&nbsp;&nbsp; <a class="today" onclick="closeCalSetToday(\'' + idtag + '\');">Today</a></td></tr></table>';
    var curHTML = "";
    var curDay = 1;
    var endDay = 0;
    var rowElement = 0;
    var startFlag = 1;
    var endFlag = 0;
    var elementClick = "";
    var celldata = "";

    ((_isLeapYear(yyyy) && mm == 2) ? endDay = 29 : endDay = dom[mm-1]);

    // calculate the lead gap
    if (startDay != 0) {
        curHTML = "<tr>";
        for (i = 0; i < startDay; i++) {
            curHTML = curHTML + '<td class="EmptyCell">&nbsp;</td>';
            rowElement++;
        }
    }

    for (i=1;i<=endDay;i++){
        (dd == i ? celldata = "CurrentCellElement" : celldata = "CellElement");

        if (rowElement == 0) {
            curHTML = curHTML + '<tr>' + '<td class="' + celldata + '" onclick="setCalendar(\'' + idtag + '\','+ yyyy +',' + mm + ',' + i +');">' + i + '</td>';
            rowElement++;
            continue;
        }

        if (rowElement > 0 && rowElement < 6) {
            curHTML = curHTML + '<td class="' + celldata + '" onclick="setCalendar(\'' + idtag + '\','+ yyyy +',' + mm + ',' + i +');">' + i + '</td>';
            rowElement++;
            continue;
        }

        if (rowElement == 6) {
            curHTML = curHTML + '<td class="' + celldata + '" onclick="setCalendar(\'' + idtag + '\','+ yyyy +',' + mm + ',' + i +');">' + i + '</td></tr>';
            rowElement = 0;
            continue;
        }
    }

    // calculate the end gap
    if (rowElement != 0) {
        for (i = rowElement; i <= 6; i++){
            curHTML = curHTML + '<td class="EmptyCell">&nbsp;</td>';
        }
    }

    curHTML = curHTML + "</tr>";
    t = document.getElementById(idtag + "Div");
    dateField = document.getElementById(idtag);
    t.innerHTML = beginTable + dateControls + calHeader + curHTML + closeControls;

    // need to write some better browser detection/positioning code here Also,
    // there is a perceived stability issue where the calendar goes offscreen
    // when the widget is right justified..Need some edge detection

    var kitName = "applewebkit/";
    var tempStr = navigator.userAgent.toLowerCase();
    var pos = tempStr.indexOf(kitName);
    var isAppleWebkit = (pos != -1);

    t.style.left = pageOffsetLeft(dateField);
    t.style.top = pageOffsetTop(dateField);
    t.style.display = "";
}

function createCalendarWidget() {
    (arguments[0] ? idtag = arguments[0] : idtag = "");
    (arguments[1] ? isEditable = arguments[1] : isEditable = "EDIT");
    (arguments[2] ? hasIcon = arguments[2] : hasIcon = "NO_ICON");
    (arguments[3] ? iconPath = arguments[3] : hasIcon = "./OU812.gif");

    (isEditable == "NO_EDIT" ? readOnly = 'readonly="readonly"' : readOnly = '');

    if (hasIcon == "ICON") {
        clicking = '';
        icon = ' <img src="' + iconPath + '" class="CalIcon" id="' + idtag + 'Icon" onmousedown="clickWidgetIcon(\'' + idtag + '\');" />';
    } else {
        clicking = 'onclick="drawCalendar(\'' + idtag + '\')"';
        icon = '';
    }

    // Edited to match SchoolBell styling
    document.write('<input name="' + idtag + '" id="' + idtag + '" type="text" class="textType" size="20" value="" ' + readOnly + ' ' + clicking + ' />' +  icon + '<br /><div id="' + idtag + 'Div" style="background: #ffffff; position: absolute; display:none;"></div>');
}
