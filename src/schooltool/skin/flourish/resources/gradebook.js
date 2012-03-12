/* This is the Javascript to be included when rendering the gradebook overview. */
function setNotEdited()
{
    edited = false;
}

function setEdited()
{
    edited = true;
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

    setEdited();
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

function makeGradeCellVisible(element) {
    var td = $(element).closest('td');
    var td_left_border = td.position().left;
    var td_right_border = td_left_border + td.outerWidth();
    var grades_left_border = $('.students').outerWidth();
    var grades_right_border = $('.gradebook').outerWidth() - $('.totals').outerWidth();
    if (td_right_border > grades_right_border) {
        var offset = td_right_border - grades_right_border;
        var current_scroll = $('.grades').scrollLeft();
        $('.grades').scrollLeft(current_scroll + offset);
    }
    if (td_left_border < grades_left_border) {
        var offset = grades_left_border - td_left_border;
        var current_scroll = $('.grades').scrollLeft();
        $('.grades').scrollLeft(current_scroll - offset);
    }
}

function findInput(element) {
    var td = $(element);
    var input = td.find('input[type="text"]');
    if (input.length > 0) {
        input.focus();
        input[0].select();
        makeGradeCellVisible(input);
        return true;
    }
    return false;
}

function focusInputHorizontally(elements) {
    elements.each(function(index, e) {
        if (findInput(e)) {
            return false;
        }
    });
}

function focusInputVertically(elements, columnIndex) {
    elements.each(function(index, e) {
        var td = $(e).find('td:eq('+columnIndex+')');
        if (td.length > 0) {
            if (findInput(td)) {
                return false;
            }
        }
    });
}

function updateGradebookPartsWidths() {
    var gradebook_w = $('.gradebook').outerWidth();
    var students_w = $('.students').outerWidth();
    var totals_headers = $('.totals th');
    var totals_w = 0;
    if (totals_headers.length > 0) {
        var totals_headers_w = totals_headers.last().outerWidth() + 1; // border
        totals_w = totals_headers.length * totals_headers_w;
        $('.totals').css({
            width: totals_w,
        });
    }
    var grades_visible_w = gradebook_w - (students_w + totals_w)
    var grades_column_count = $('.grades thead tr:first-child th:not(.placeholder)').length;
    var grades_margin_left = students_w;
    var grades_margin_right = totals_w;
    $('.grades').css({
        marginLeft: grades_margin_left,
        marginRight: grades_margin_right,
    });
    if (grades_column_count > 0) {
        var grades_column_w = $('.grades th:first').outerWidth();
        var grades_max = Math.floor(grades_visible_w / grades_column_w);
        if (grades_column_count > grades_max) {
            var grades_column_w = Math.floor(grades_visible_w / grades_max);
            $('.grades th').css('width', grades_column_w);
            $('.grades td').css('width', grades_column_w);
            $('.placeholder').hide();
        }
    }
}

$(document).ready(function() {
    updateGradebookPartsWidths();
    // row colors
    $('.students tbody tr:odd').addClass('odd');
    $('.grades tbody tr:odd').addClass('odd');
    $('.totals tbody tr:odd').addClass('odd');
    // cell borders
    $('.grades table tr > *:first-child').css({
        borderLeft: 'none',
    });
    var last_column_index = $('.grades tr:first-child th:visible').index();
    $('.grades table tr').find('th:eq('+last_column_index+')').css({
        borderRight: 'none',
    });
    $('.grades table tr').find('td:eq('+last_column_index+')').css({
        borderRight: 'none',
    });
    // cell navigation
    $('.grades input[type="text"]').click(function() {
        this.select();
    });
    $('.grades td').click(function() {
        makeGradeCellVisible(this);
    });
    $('.grades input[type="text"]').keydown(function(e) {
        var td = $(this).parent();
        var tr = td.parent()
        switch(e.keyCode) {
        case 37: // left
            focusInputHorizontally(td.prevUntil('tr'));
            e.preventDefault();
            break;
        case 39: // right
            focusInputHorizontally(td.nextAll());
            e.preventDefault();
            break;
        case 38: // up
            focusInputVertically(tr.prevUntil('tbody'), td.index());
            e.preventDefault();
            break;
        case 40: // down
            focusInputVertically(tr.nextAll(), td.index());
            e.preventDefault();
            break;
        }
    });
});
