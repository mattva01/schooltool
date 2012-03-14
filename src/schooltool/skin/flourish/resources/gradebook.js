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
    var grades_left_border = $('#students-part').outerWidth();
    var grades_right_border = $('#gradebook').outerWidth() - $('#totals-part').outerWidth();
    var grades = $('#grades-part');
    if (cell_right_border > grades_right_border) {
        var offset = cell_right_border - grades_right_border;
        var current_scroll = grades.scrollLeft();
        grades.scrollLeft(current_scroll + offset);
    }
    if (cell_left_border < grades_left_border) {
        var offset = grades_left_border - cell_left_border;
        var current_scroll = grades.scrollLeft();
        grades.scrollLeft(current_scroll - offset);
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
        var td = $(e).find('td').eq(columnIndex);
        if ((td.length > 0) && isScorable(td)) {
            input = getInput(td);
            input[0].select();
            input.focus();
            makeGradeCellVisible(td);
            return false;
        }
    });
}

function updateGradebookPartsWidths(form) {
    var gradebook_w = form.find('#gradebook').outerWidth();
    var students_w = form.find('#students-part').outerWidth();
    var totals = form.find('#totals-part');
    var totals_headers = totals.find('th');
    var grades = form.find('#grades-part');
    var totals_w = 0;
    if (totals_headers.length > 0) {
        var totals_headers_w = totals_headers.first().outerWidth() + 1; // border
        totals_w = totals_headers.length * totals_headers_w;
        totals.css({
            width: totals_w,
        });
    }
    var grades_visible_w = gradebook_w - (students_w + totals_w)
    var grades_column_count = grades.find('th').not('.placeholder').length;
    var grades_margin_left = students_w;
    var grades_margin_right = totals_w;
    grades.css({
        marginLeft: grades_margin_left,
        marginRight: grades_margin_right,
    });
    if (grades_column_count > 0) {
        var grades_column_w = grades.find('th').first().outerWidth();
        var grades_max = Math.floor(grades_visible_w / grades_column_w);
        if (grades_column_count > grades_max) {
            var grades_column_w = Math.floor(grades_visible_w / grades_max);
            var grades_column_css = {'width': grades_column_w};
            grades.find('th').css(grades_column_css);
            grades.find('td').css(grades_column_css);
            grades.find('.placeholder').hide();
        }
    }
}

function cellInputName(td) {
    var columnHeader = findColumnHeader(td);
    var rowHeader = findRowHeader(td);
    return [columnHeader.attr('id'), '_', rowHeader.attr('id')].join('');
}

function findRowHeader(td) {
    var rowIndex = td.parent().index();
    return $('#students-part').find('td').eq(rowIndex);
}

function findColumnHeader(td) {
    var columnIndex = td.index();
    return $('#grades-part').find('th').eq(columnIndex);
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

function buildURL(base_url, view) {
    return [base_url, '/', view].join('');
}

function preloadNamePopup(form) {
    var base_url = form.attr('action');
    var popup_links = form.find('#students-part').find('thead').find('.popup_link');
    popup_links.each(function(index, element) {
        var link = $(element);
        var url = buildURL(base_url, 'name_popup_menu');
        loadPopup(link, url, {}, false);
    });
}

function preloadActivityPopups(form) {
    var popup_links = form.find('#grades-part').find('.popup_link');
    var base_url = form.attr('action');
    popup_links.each(function(index, element) {
        var link = $(element);
        var activity_id = link.parent().attr('id');
        var attrs = {'activity_id': activity_id};
        var url = buildURL(base_url, 'activity_popup_menu');
        loadPopup(link, url, attrs, true);
    });
}

function preloadStudentPopups(form) {
    var base_url = form.attr('action');
    var popup_links = form.find('#students-part').find('tbody').find('.popup_link');
    popup_links.each(function(index, element) {
        var link = $(element);
        var student_id = link.parent().attr('id');
        var attrs = {'student_id': student_id};
        var url = buildURL(base_url, 'student_popup_menu');
        loadPopup(link, url, attrs, false);
    });
}

function preloadTotalPopups(form) {
    var base_url = form.attr('action');
    var popup_links = form.find('#totals-part').find('.popup_link');
    popup_links.each(function(index, element) {
        var link = $(element);
        var column_id = link.parent().attr('id').split('_')[1]; // id is column_*
        var attrs = {'column_id': column_id};
        var url = buildURL(base_url, 'total_popup_menu');
        loadPopup(link, url, attrs, true);
    });
}

function preloadPopups(form) {
    preloadNamePopup(form);
    preloadActivityPopups(form);
    preloadStudentPopups(form);
    preloadTotalPopups(form);
}

function appendSpinner(link) {
    var spinner = ST.images.spinner();
    var li = $('<li class="header"></li').append(spinner);
    link.prev().append(li);
}

function loadPopup(link, url, data, calculateLeft) {
    appendSpinner(link);
    $.ajax({
        url: url,
        dataType: 'html',
        type: 'get',
        data: data,
        context: link,
        success: function(data) {
            var is_visible = this.prev().is(':visible');
            this.prev().replaceWith(data);
            if (is_visible) {
                var popup = this.prev();
                if (calculateLeft) {
                    var left = calculatePopupLeft(popup);
                    popup.css('left', left+'px');
                }
                popup.addClass('popup_active').show();
            }
        }
    });
}

function calculatePopupLeft(popup) {
    var th = popup.parent();
    var part = popup.closest('.gradebook-part');
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

function preloadFilldown(form) {
    var url = buildURL(form.attr('action'), 'filldown');
    $.ajax({
        url: url,
        dataType: 'html',
        type: 'get',
        context: form,
        success: function(data) {
            this.before(data);
        }
    });
}

function hidePopup(form) {
    form.find('.popup_active').hide().removeClass('popup_active');
}

$(document).ready(function() {
    var form = $('#grid-form');
    // gradebook-part width calculation
    updateGradebookPartsWidths(form);
    // row colors
    $('.gradebook-part').find('tbody').find('tr:odd').addClass('odd');
    // fill down
    preloadFilldown(form);
    // popup menus
    preloadPopups(form);
    var gradebook = form.find('#gradebook');
    gradebook.on('click', '.popup_link', function(e) {
        var link = $(this);
        var popup = link.prev();
        if (link.parent().is('th')) {
            var popup = link.prev();
            var left = calculatePopupLeft(popup);
            popup.css('left', left+'px');
        }
        hidePopup(form);
        popup.addClass('popup_active').show();
        e.preventDefault();
    });
    var grades = form.find('#grades-part');
    grades.scroll(function() {
        hidePopup(form);
    });
    $(document).click(function(e) {
        if (!$(e.target).hasClass('popup_link')) {
            hidePopup(form);
        }
    });
    // cell navigation
    grades.on('click', 'td', function() {
        var td = $(this);
        makeGradeCellVisible(td);
        if (isScorable(td)) {
            var input = getInput(td);
            input[0].select();
            input.focus();
        }
    });
    grades.on('click', 'input', function() {
        this.select();
    });
    grades.on('blur', 'input', function() {
        var td = $(this).parent();
        if ($(this).val() === td.attr('original')) {
            removeInput(td);
        }
    });
    grades.on('keyup', 'input', function() {
        var input = $(this);
        var td = input.parent();
        if (input.val() !== td.attr('original')) {
            if (this.timer) {
                clearTimeout(this.timer);
            }
            var data = {
                'activity_id': findColumnHeader(td).attr('id'),
                'score': input.val()
            }
            var url = form.attr('action') + '/validate_score_json';
            this.timer = setTimeout(function () {
                $.ajax({
                    url: url,
                    data: data,
                    dataType: 'json',
                    type: 'get',
                    success: function(data) {
                        input.removeClass();
                        input.addClass(data.css_class);
                    }
                });
            }, 200);
        }
    });
    grades.on('keydown', 'input', function(e) {
        var td = $(this).parent();
        var tr = td.parent()
        switch(e.keyCode) {
        case 27: // escape
            $(this).val(td.attr('original'));
            $(this).blur();
            e.preventDefault();
            break;
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
    // filldown
    form.on('click', '.filldown', function() {
        hidePopup(form);
        var container = $('#filldown-dialog-container');
        var cell = $(this).closest('th');
        var popup_link = cell.find('.popup_link');
        var description = cell.find('.activity-description');
        container.find('span').html(popup_link.attr('title'));
        container.find('p').html(description.html());
        var idx = cell.parent().children().index(cell);
        var rows = cell.closest('table').find('tbody').find('tr');
        var cells = [];
        rows.each(function(i, row) {
            var cell = $(row).children()[idx];
            cells.push(cell);
        })
        container.data('schooltool.gradebook-filldown-dialog-cells', cells);
        var filldown_title = container.find('.filldown-dialog-title').text();
        container.dialog({
            'title': filldown_title,
            'resizable': false,
            'width': 306,
            'minHeight': 105,
            'dialogClass': 'narrow-dialog'
        });
        return false;
    });
    $('body').on('click', '.filldown-cancel', function() {
        var container = $('#filldown-dialog-container');
        container.find('#filldown_value').val('');
        container.dialog('close');
        return false;
    });
    $('body').on('click', '.filldown-submit', function() {
        var container = $('#filldown-dialog-container');
        var fillval = container.find('#filldown_value').val();
        if (fillval) {
            var cells = container.data('schooltool.gradebook-filldown-dialog-cells');
            $(cells).each(function(i, cell) {
                var cell = $(cell);
                if (cell.is(':empty')) {
                    var input = getInput(cell);
                    input.val(fillval);
                    input.trigger('keyup');
                    input.blur();
                }
            });
        }
        container.dialog('close');
        return false;
    });
});
