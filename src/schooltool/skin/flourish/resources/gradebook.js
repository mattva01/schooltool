/* This is the Javascript to be included when rendering the gradebook overview. */
function setNotEdited()
{
    edited = false;
}

function checkChanges()
{
    if (!edited)
        return;
    saveFlag = window.confirm(warningText);
    if (saveFlag == true)
        {
        button = document.getElementsByName('UPDATE_SUBMIT')[0];
        button.click();
        }
    else
        return true;
}

function onLoadHandler()
{
    // highlight error values
    for (a = 0; a < numactivities; a++)
    {
        activity = activities[a];
        for (s = 0; s < numstudents; s++)
        {
            name = activity + '_' + students[s];
            value = document.getElementById(name).value;
            setBackgroundColor(name, activity, value, true);
        }
    }
}

function handleCellFocus(cell, activity)
{
    currentCell = cell;
    cell.select();
}

function spreadsheetBehaviour(e)
{
    var keynum;
    if(window.event) // IE
    {
        keynum = e.keyCode;
    }
    else if(e.which) // Netscape/Firefox/Opera
    {
        keynum = e.which;
    }

    var my_name = currentCell.id;
    var s, a, done;
    done = new Boolean(false);

    for (s = 0; s != numstudents; s++)
    {
        for (a = 0; a != numactivities; a++)
        {
            try_name = activities[a] + '_' + students[s]
            if (try_name == my_name)
            {
                done = true;
                break;
            }
        }
        if (done == true)
            break;
    }

    var i_stayed_put = new Boolean(true);
    if (keynum == 37) // left arrow
    {
        if (a != 0) { a--; i_stayed_put = false;}
    }
    if (keynum == 39) // right arrow
    {
        if (a != numactivities - 1) {a++; i_stayed_put = false;}
    }
    if (keynum == 38) // up arrow
    {
        if (s != 0) {s--; i_stayed_put = false;}
    }
    if ((keynum == 40) || (keynum == 13)) // down arrow or enter
    {
        if (s != numstudents - 1) {s++; i_stayed_put = false;}
    }

    if (i_stayed_put == true)
        return true;
    var newname = activities[a] + '_' + students[s];
    var el = document.getElementsByName(newname)[0]
    el.focus();
    return false;
}

function checkValid(e, name)
{
    var activity = name.split('_')[0];
    if(activity == "fd")
        activity = name.split('_')[1];
    if (e == null)
        return true;

    var keynum;
    if(window.event) // IE
	{ 
	    keynum = e.keyCode;
	}
    else if(e.which) // Netscape/Firefox/Opera
	{
	    keynum = e.which;
	}
    if (keynum < 48 || (keynum > 57 && keynum < 65) || (keynum > 90 && keynum < 97) || keynum > 122)
	{
	    return true;
	}

    edited = true;
    var element = document.getElementById(name);
    var elementCell = document.getElementById(name+'_cell');
    var value = element.value;

    return setBackgroundColor(name, activity, value, false);
}

function setBackgroundColor(name, activity, value, errors_only)
{
    changeBackgroundColor(name+'_cell', 'default_bg');

    if (value == '')
        return true;

    // handle validation of discrete score system
    var actScores = scores[activity];
    if (actScores[0] == 'd')
    {
        for(var index in actScores)
        {
            if (index > 0 && value == actScores[index])
            {
                if (!errors_only)
                    changeBackgroundColor(name+'_cell', 'changed_bg');
                return true;
            }
        }  
        changeBackgroundColor(name+'_cell', 'error_bg');
        return false;   
    }

    // handle validation of ranged score system
    else
    {
        var min = parseInt(actScores[1]);
        var max = parseInt(actScores[2]);
        var intValue = parseInt(value);
        var regex = /[0-9]+$/;
        if (!value.match(regex) || intValue < min)
        {
            changeBackgroundColor(name+'_cell', 'error_bg');
            return false;   
        }
        if (errors_only)
            return true;
        if (intValue > max)
        {
            changeBackgroundColor(name+'_cell', 'warning_bg');
            return true;
        }
    }

    changeBackgroundColor(name+'_cell', 'changed_bg');
    return true;    
}

function changeBackgroundColor(id, klass) {
    obj = document.getElementById(id);
    $(obj).removeClass('default_bg');
    $(obj).removeClass('changed_bg');
    $(obj).removeClass('warning_bg');
    $(obj).removeClass('error_bg');
    $(obj).addClass(klass);
}

// Changes made for flourish

function updateWidths() {
    // Used to calculate the margins of the div.grades area and
    // placeholders (when there are not enough activity columns
    // to fill the grades space)
    var gradebook_width = $('.gradebook').width();
    var students_width = $('.students').outerWidth();
    var totals_width = $('.totals').outerWidth();
    if (students_width) {
        $('.grades').css('marginLeft', students_width + 'px');
    }
    if (totals_width) {
        $('.grades').css('marginRight', totals_width + 'px');
    }
    activities_width = 0;
    $('.grades th.activity-title').each(function() {
        activities_width += $(this).outerWidth();
    });
    var grades_width = $('.grades').width();
    if (grades_width > activities_width) {
        placeholder_width = grades_width - activities_width;
        $('.placeholder').css('width', placeholder_width +'px');
        $('.placeholder').show();
    } else {
        $('.placeholder').hide();
    }
}

$(window).load(function() {
    // XXX: Chrome doesn't calculate the widths correctly
    //      when this call is in $(document).ready()
    //      because it loads js and css in paralell
    //      and the width information may not be available yet
    updateWidths();
});

$(document).ready(function() {
    // popup menus
    $('.popup_link').click(function(e) {
        $('.popup_active').hide().removeClass('popup_active');
        $(this).parent().prev('ul.popup_menu').addClass('popup_active');
        $('.popup_active').show();
        e.preventDefault();
    });
    $(document).click(function(e) {
        if ($(e.target).hasClass('popup_link') == false) {
            $('.popup_active').hide().removeClass('popup_active');
        }
    });
    // row colors
    $('.students tbody tr:odd').addClass('odd');
    $('.grades tbody tr:odd').addClass('odd');
    $('.totals tbody tr:odd').addClass('odd');
    // zoom buttons
    var factor = 1.125;
    var min_size = 7;
    var max_size = 18;
    var default_size = 10;
    $('.zoom-button').click(function () {
        var form = $('.grid-form');
        var current_size = form.css('fontSize');
        var num = parseFloat(current_size, default_size);
        var unit = current_size.slice(-2);
        if (this.id == 'zoom-in') {
            num *= factor;
        } else if (this.id == 'zoom-out') {
            num /= factor;
        } else if (this.id == 'zoom-normal') {
            num = default_size;
        }
        if (num >= min_size && num <= max_size) {
            form.css('fontSize', num + unit);
        }
        updateWidths();
    });
});
