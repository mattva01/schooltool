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
    var cell = $(element);
    var cell_left_border = cell.position().left;
    var cell_right_border = cell_left_border + cell.outerWidth();
    var grades_left_border = $('.students').outerWidth();
    var grades_right_border = $('.gradebook').outerWidth() - $('.totals').outerWidth();
    if (cell_right_border > grades_right_border) {
        var offset = cell_right_border - grades_right_border;
        var current_scroll = $('.grades').scrollLeft();
        $('.grades').scrollLeft(current_scroll + offset);
    }
    if (cell_left_border < grades_left_border) {
        var offset = grades_left_border - cell_left_border;
        var current_scroll = $('.grades').scrollLeft();
        $('.grades').scrollLeft(current_scroll - offset);
    }
}

function focusInputHorizontally(elements) {
    var input;
    elements.each(function(index, e) {
        var element = $(e);
        if (isScorable(element)) {
            input = getInput(element);
            input[0].select();
            input.focus();
            makeGradeCellVisible(element);
            return false;
        }
    });
}

function focusInputVertically(elements, columnIndex) {
    elements.each(function(index, e) {
        var td = $(e).find('td:eq('+columnIndex+')');
        if ((td.length > 0) && isScorable(td)) {
            input = getInput(td);
            input[0].select();
            input.focus();
            makeGradeCellVisible(td);
            return false;
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
    var grades_column_selector = '.grades tr:first-child th:not(.placeholder)';
    var grades_column_count = $(grades_column_selector).length;
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

function cellInputName(td) {
    var columnHeader = findColumnHeader(td);
    var rowHeader = findRowHeader(td);
    return columnHeader.attr('id') + '_' + rowHeader.attr('id');
}

function findRowHeader(td) {
    var rowIndex = td.parent().index();
    var table = $('.students table');
    return table.find('tbody td:eq('+rowIndex+')');
}

function findColumnHeader(td) {
    var columnIndex = td.index();
    var table = $('.grades table');
    return table.find('thead tr:first-child th:eq('+columnIndex+')');
}

function isScorable(td) {
    var columnHeader = findColumnHeader(td);
    return columnHeader.hasClass('scorable');
}

function getInput(td) {
    if (td.find('input').length < 1) {
        var new_input = $('<input type="text" />');
        var name = cellInputName(td);
        var value = td.text();
        new_input.attr('name', name);
        new_input.attr('value', value);
        td.attr('original', value);
        td.html($('<div>').append(new_input).html());
    }
    return td.find('input');
}

function removeInput(td) {
    td.empty();
    td.html(td.attr('original'));
    td.removeAttr('original');
}

function preloadActivityPopups() {
    var popup_links = $('.grades thead a.popup_link');
    popup_links.each(function(index, element) {
        loadActivityPopup($(element));
    });
}

function preloadStudentPopups() {
    var popup_links = $('.students tbody a.popup_link');
    popup_links.each(function(index, element) {
        loadStudentPopup($(element));
    });
}

function preloadPopups() {
    loadNamePopup();
    preloadActivityPopups();
    preloadStudentPopups();
}

function loadNamePopup() {
    var element = $('.students thead a.popup_link')[0];
    var link = $(element);
    var gradebook_url = $('.grid-form').attr('action');
    if (link.prev('ul.popup_menu').children().length < 1) {
        var spinner = ST.images.spinner();
        var li = $('<li class="header"></li').append(spinner);
        link.prev('ul.popup_menu').append(li);
        var url = gradebook_url+'/name_popup_menu';
        $.ajax({
            url: url,
            dataType: 'html',
            type: 'get',
            context: link,
            success: function(data) {
                var is_visible = this.prev('ul.popup_menu').is(':visible');
                this.prev('ul.popup_menu').replaceWith(data);
                if (is_visible) {
                    this.prev('ul.popup_menu').addClass('popup_active').show();
                }
            }
        });
    }
}

function loadActivityPopup(link) {
    var gradebook_url = $('.grid-form').attr('action');
    if (link.prev('ul.popup_menu').children().length < 1) {
        var spinner = ST.images.spinner();
        var li = $('<li class="header"></li').append(spinner);
        link.prev('ul.popup_menu').append(li);
        var activity_id = link.parent().attr('id');
        var url = gradebook_url+'/activity_popup_menu?activity_id='+activity_id;
        $.ajax({
            url: url,
            dataType: 'html',
            type: 'get',
            context: link,
            success: function(data) {
                var is_visible = this.prev('ul.popup_menu').is(':visible');
                this.prev('ul.popup_menu').replaceWith(data);
                if (is_visible) {
                    var left = calculatePopupLeft(this);
                    this.prev('ul.popup_menu').css('left', left+'px');
                    this.prev('ul.popup_menu').addClass('popup_active').show();
                }
            }
        });
    }
}

function loadStudentPopup(link) {
    var gradebook_url = $('.grid-form').attr('action');
    if (link.prev('ul.popup_menu').children().length < 1) {
        var spinner = ST.images.spinner();
        var li = $('<li class="header"></li').append(spinner);
        link.prev('ul.popup_menu').append(li);
        var student_id = link.parent().attr('id');
        var url = gradebook_url+'/student_popup_menu?student_id='+student_id;
        $.ajax({
            url: url,
            dataType: 'html',
            type: 'get',
            context: link,
            success: function(data) {
                var is_visible = this.prev('ul.popup_menu').is(':visible');
                this.prev('ul.popup_menu').replaceWith(data);
                if (is_visible) {
                    this.prev('ul.popup_menu').addClass('popup_active').show();
                }
            }
        });
    }
}

function calculatePopupLeft(link) {
    var th = link.closest('th');
    var popup = link.prev('ul.popup_menu');
    var part = link.closest('.gradebook-part');
    var part_margin_left = part.css('marginLeft').replace('px','');
    part_margin_left = parseInt(part_margin_left);
    var popup_right = th.position().left - part_margin_left + popup.outerWidth();
    if (popup_right > part.outerWidth()) {
        var left = th.position().left + th.outerWidth() - popup.outerWidth();
    } else {
        var left = th.position().left;
    }
    return left;
}

$(document).ready(function() {
    // popup menus
    preloadPopups();
    $('.popup_link').click(function(e) {
        var link = $(this);
        var popup = link.prev('ul.popup_menu');
        if (link.closest('th').length > 0) {
            var left = calculatePopupLeft(link);
            popup.css('left', left+'px');
        }
        $('.popup_active').hide().removeClass('popup_active');
        popup.addClass('popup_active').show();
        e.preventDefault();
    });
    $('.grades').scroll(function() {
        $('.popup_active').hide().removeClass('popup_active');
    });
    $(document).click(function(e) {
        if ($(e.target).hasClass('popup_link') == false) {
            $('.popup_active').hide().removeClass('popup_active');
        }
    });
    // gradebook-part width calculation
    updateGradebookPartsWidths();
    // row colors
    $('.students tbody tr:odd').addClass('odd');
    $('.grades tbody tr:odd').addClass('odd');
    $('.totals tbody tr:odd').addClass('odd');
    // cell navigation
    $('.grades td').click(function() {
        var td = $(this);
        makeGradeCellVisible(td);
        if (isScorable(td)) {
            var input = getInput(td);
            input[0].select();
            input.focus();
        }
    });
    $('.grades').on('click', 'input', function() {
        this.select();
    });
    $('.grades').on('blur', 'input', function() {
        var td = $(this).parent();
        if ($(this).val() === td.attr('original')) {
            removeInput(td);
        }
    });
    $('.grades').on('keyup', 'input', function() {
        var input = $(this);
        var td = input.parent();
        if (input.val() !== td.attr('original')) {
            if (this.timer) {
                clearTimeout(this.timer);
            }
            var data = Array();
            data.push({
                name: 'action',
                value: 'validate_score'
            });
            data.push({
                name: 'activity_id',
                value: findColumnHeader(td).attr('id')
            });
            data.push({
                name: 'score',
                value: input.val()
            });
            var url = input.closest('form').attr('action') + '/ajax';
            this.timer = setTimeout(function () {
                $.ajax({
                    url: url,
                    data: data,
                    dataType: 'json',
                    type: 'post',
                    success: function(data) {
                        input.removeClass();
                        input.addClass(data.css_class);
                    }
                });
            }, 200);
        }
    });
    $('.grades').on('keydown', 'input', function(e) {
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
        case 13: // enter
        case 40: // down
            focusInputVertically(tr.nextAll(), td.index());
            e.preventDefault();
            break;
        }
    });
});
