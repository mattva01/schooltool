// Changes made for flourish

function makeGradeCellVisible(element) {
    var cell = $(element);
    var cell_left_border = cell.position().left;
    var cell_right_border = cell_left_border + cell.outerWidth();
    var grades_left_border = $('#students-part').outerWidth();
    var grades_right_border = ($('#gradebook').outerWidth() -
                               $('#totals-part').outerWidth());
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
    var students = form.find('#students-part');
    var students_w = students.outerWidth();
    var totals = form.find('#totals-part');
    var totals_headers = totals.find('tr').first().find('th');
    var grades = form.find('#grades-part');
    var totals_w = 0;
    var base_font_size = form.data('base-font-size');
    if (totals_headers.length > 0) {
        if (!totals.data('base-total-column-width')) {
            totals.data('base-total-column-width',
                        totals_headers.first().outerWidth());
        }
        totals_w = (totals_headers.length *
                    totals.data('base-total-column-width'));
        totals.find('thead').find('tr').css({
            height: students.find('thead').height()
        });
        totals.css({
            width: Math.floor(totals_w/base_font_size)+'em'
        });
    }
    var grades_margin_left = students_w;
    var grades_margin_right = totals_w;
    grades.css({
        marginLeft: grades_margin_left,
        marginRight: Math.floor(totals_w/base_font_size)+'em'
    });
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

function fillPopupMenu(link) {
    var data = link.data('popup-menu-data');
    var popup = link.prev();
    popup.empty();
    if (!data) {
        return;
    }
    var header = $('<li class="header"></li>');
    header.text(data.header);
    popup.append(header);
    $.each(data.options, function(i, el) {
        var li = $('<li></li>');
        if (!el.options) {
            var a = $('<a></a>');
            a.text(el.label);
            a.attr('href', el.url);
            if (el.css_class) {
                a.addClass(el.css_class);
            }
            li.append(a);
        } else {
            var span = $('<span class="hover_link"></span>');
            span.text(el.header);
            li.append(span);
            var hover_ul = $('<ul class="hover_menu"></ul>');
            $.each(el.options, function(j, option) {
                var hover_li = $('<li></li>');
                if (option.current) {
                    hover_li.addClass('current');
                    hover_li.text(option.label);
                } else {
                    var hover_a = $('<a></a>');
                    hover_a.attr('href', option.url);
                    hover_a.text(option.label);
                    hover_li.append(hover_a);
                }
                hover_ul.append(hover_li);
            });
            li.append(hover_ul);
        }
        popup.append(li);
    });
}

function loadPopup(link, url, data, calculateLeft) {
    insertPopupMenu(link);
    $.ajax({
        url: url,
        dataType: 'json',
        type: 'get',
        data: data,
        context: link,
        success: function(data) {
            var is_visible = this.prev().is(':visible');
            this.data('popup-menu-data', data);
            fillPopupMenu(this);
            if (is_visible) {
                var popup = this.prev();
                if (calculateLeft) {
                    var left = calculatePopupLeft(popup);
                    popup.css('left', left);
                }
                popup.addClass('popup_active').show();
            }
        }
    });
}

function insertPopupMenu(link) {
    var popup_menu = $('<ul></ul>');
    var spinner = ST.images.spinner();
    var li = $('<li class="header"></li>').append(spinner);
    popup_menu.addClass('popup_menu').append(li);
    link.before(popup_menu);
}

function calculatePopupLeft(popup) {
    var th = popup.parent();
    var part = popup.closest('.gradebook-part');
    var part_margin_left = parseInt(part.css('marginLeft'));
    var popup_right = (th.position().left - part_margin_left +
                       popup.outerWidth());
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

function preloadCommentCell(form) {
    var url = buildURL(form.attr('action'), 'comment_cell');
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

function isFirstTabVisible(third_nav) {
    return third_nav.position().left == 0;
}

function isLastTabVisible(third_nav) {
    var tab_width;
    var max_tab_count;
    var tabs = third_nav.children();
    var container_width = third_nav.parent().outerWidth();
    if (tabs.length) {
        tab_width = tabs.first().outerWidth();
        max_tab_count = Math.floor(container_width/tab_width);
        if (tabs.length <= max_tab_count) {
            return true;
        }
    }
    var third_nav_left = third_nav.position().left;
    var limit = -(tabs.length - max_tab_count) * tab_width;
    return third_nav_left == limit;
}

function createWorksheetsList() {
    var ul = $('<ul id="worksheets-list"></ul>');
    var tabs = $('.third-nav li');
    tabs.each(function(i, el) {
        var tab = $(el).clone();
        var link = tab.find('a');
        tab.find('a').text(link.attr('title'));
        ul.append(tab);
    });
    ul.addClass('popup_menu');
    ul.addClass('worksheets-list');
    return ul;
}

function removeSavingWarning() {
    window.onbeforeunload = null;
}

function initGradebook() {
    var form = $('#grid-form');
    form.data('base-font-size', parseInt(form.css('fontSize')));
    // gradebook-part width calculation
    updateGradebookPartsWidths(form);
    // row colors
    $('.gradebook-part').find('tbody').find('tr:odd').addClass('odd');
    // fill down
    preloadFilldown(form);
    // comment cell
    preloadCommentCell(form);
    // popup menus
    preloadPopups(form);
    var gradebook = form.find('#gradebook');
    gradebook.on('click', '.popup_link', function(e) {
        var link = $(this);
        var popup = link.prev();
        if (link.parent().is('th')) {
            var popup = link.prev();
            var left = calculatePopupLeft(popup);
            popup.css('left', left);
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
        if (!$(e.target).hasClass('navbar-list-worksheets')) {
            var list = $('#worksheets-list');
            if (list.is(':visible')) {
                list.slideUp('fast');
                $('#navbar-list-worksheets').toggleClass(
                    'navbar-list-worksheets-active');
            }
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
            };
            var url = form.attr('action') + '/validate_score';
            this.timer = setTimeout(function () {
                $.ajax({
                    url: url,
                    data: data,
                    dataType: 'json',
                    type: 'get',
                    success: function(data) {
                        if (data.hasOwnProperty('score')) {
                            input.val(data.score);
                        }
                        input.removeClass();
                        var css_class = 'valid';
                        if (!data.is_valid) {
                            css_class = 'error';
                        } else if (data.is_extracredit) {
                            css_class = 'extracredit';
                        }
                        input.addClass(css_class);
                    }
                });
            }, 200);
        }
    });
    grades.on('keydown', 'input', function(e) {
        var td = $(this).parent();
        var tr = td.parent();
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
        });
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
            var cells = container.data(
                'schooltool.gradebook-filldown-dialog-cells');
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
        container.find('#filldown_value').val('');
        container.dialog('close');
        return false;
    });
    // comment-cell
    form.on('click', '.comment-cell', function() {
        hidePopup(form);
        var container = $('#comment-cell-dialog-container');
        var cell = $(this).closest('tr');
        var student_idx = cell.parent().children().index(cell);
        var student = $('#students-part tbody tr')[student_idx];
        var student_title = $(student).find('li')[0].innerHTML;
        var student_id = $(student).find('td').attr('id');
        var activity_idx = $(this).parent().children().index(this);
        var activity = $('#grades-part th')[activity_idx];
        var activity_id = $(activity).attr('id');
        var popup_link = $(activity).find('.popup_link');
        var description = $(activity).find('.activity-description');
        var value = $(this).attr('hidden_value');
        var dialog_title = container.find('#comment-cell-dialog-title').attr('dialog_title')
        container.find('#comment-cell-dialog-title').text(student_title);
        container.find('#comment-student-id').val(student_id);
        container.find('#comment-activity-id').val(activity_id);
        container.find('#form-widgets-value').val(value);
        FCKeditorAPI.Instances['form-widgets-value'].SetHTML(value)
        container.find('span').html(popup_link.attr('title'));
        container.find('p').html(description.html());
        container.dialog({
            'title': dialog_title,
            'resizable': false,
            'width': 306,
            'minHeight': 105,
            'dialogClass': 'narrow-dialog',
            'modal': true
        });
        // XXX - this should have worked but doesn't
        //FCKeditorAPI.Instances['form-widgets-value'].EditorDocument.body.focus()
        return false;
    });
    $('body').on('click', '.comment-cell-cancel', function() {
        var container = $('#comment-cell-dialog-container');
        container.find('#form-widgets-value').val('');
        container.dialog('close');
        return false;
    });
    $('body').on('click', '.comment-cell-submit', function() {
        var student_id = $('#comment-student-id').val();
        var activity_id = $('#comment-activity-id').val();
        var form = $('#grid-form');
        form.append($('<input type="hidden"/>').attr({
            'name': activity_id + '_' + student_id,
            'value': FCKeditorAPI.Instances['form-widgets-value'].GetHTML()
        }));
        removeSavingWarning();
        form.submit();
        return false;
    });
    // Zoom buttons
    var normal_width = 752;
    var wide_width = 944;
    var font_size_base = 10;
    var factor = 1;
    var minimum_font_size = 8;
    var maximum_font_size = 14;
    $('.buttons').find('.collapse').hide();
    $('#gradebook-controls').on('click', '.zoom-in', function() {
        var current_font_size = parseInt(form.css('fontSize'));
        if (current_font_size < maximum_font_size) {
            form.css({
                fontSize: '+='+factor
            });
            updateGradebookPartsWidths(form);
        }
    });
    $('#gradebook-controls').on('click', '.zoom-out', function() {
        var current_font_size = parseInt(form.css('fontSize'));
        if (current_font_size > minimum_font_size) {
            form.css({
                fontSize: '-='+factor
            });
            updateGradebookPartsWidths(form);
        }
    });
    $('#gradebook-controls').on('click', '.zoom-normal', function() {
        form.css({
            fontSize: font_size_base
        });
        updateGradebookPartsWidths(form);
    });
    $('#gradebook-controls').on('click', '.expand', function() {
        $('.sidebar').hide();
        $('#third-nav-container').css({
            width: wide_width-77,
            left: 42
        });
        $('#navbar-go-previous').css({
            left: 16
        });
        $(this).closest('.widecontainer').css({
            width: wide_width
        });
        updateGradebookPartsWidths(form);
        $(this).hide();
        $('.collapse').show();
    });
    $('#gradebook-controls').on('click', '.collapse', function() {
        $('.sidebar').show();
        $('#third-nav-container').css({
            width: normal_width-77,
            left: 234
        });
        $('#navbar-go-previous').css({
            left: 208
        });
        $(this).closest('.widecontainer').css({
            width: normal_width
        });
        updateGradebookPartsWidths(form);
        $(this).hide();
        $('.expand').show();
    });
    // tertiary navigation
    var third_nav_container = $('#third-nav-container');
    var third_nav = third_nav_container.find('.third-nav');
    var active_tab = third_nav.find('.active');
    var tab_width = active_tab.outerWidth();
    var go_previous = $('#navbar-go-previous');
    var go_next = $('#navbar-go-next');
    var list_worksheets = $('#navbar-list-worksheets');
    if (active_tab.index() > 4) {
        var scrollTo = tab_width * (active_tab.index() - 4);
        third_nav_container.scrollTo(scrollTo, 0, {axis: 'x'});
    } else {
        go_previous.addClass('navbar-arrow-inactive');
    }
    if (third_nav.children().length < 6) {
        go_next.addClass('navbar-arrow-inactive');
        list_worksheets.addClass('navbar-arrow-inactive');
    }
    third_nav_container.scroll(function(e) {
        go_previous.toggleClass('navbar-arrow-inactive',
                                isFirstTabVisible(third_nav));
        go_next.toggleClass('navbar-arrow-inactive',
                            isLastTabVisible(third_nav));
    });
    go_previous.click(function(e) {
        if (!isFirstTabVisible(third_nav)) {
            third_nav_container.scrollTo('-='+tab_width, 0, {axis: 'x'});
        }
        e.preventDefault();
    });
    go_next.click(function(e) {
        if (!isLastTabVisible(third_nav)) {
            third_nav_container.scrollTo('+='+tab_width, 0, {axis: 'x'});
        }
        e.preventDefault();
    });
    list_worksheets.click(function(e) {
        if (!$(this).hasClass('navbar-arrow-inactive')) {
            if ($('#worksheets-list').length < 1) {
                var ul = createWorksheetsList();
                $(this).after(ul);
            }
            $('#worksheets-list').slideToggle('fast');
            $(this).toggleClass('navbar-list-worksheets-active');
        }
        e.preventDefault();
    });
    // ignore warning dialog when clicking save button
    form.on('click', 'input[type="submit"]', function() {
        removeSavingWarning();
    });
}

$(document).ready(initGradebook);

// warning dialog for unsaved changes
window.onbeforeunload = function() {
    if ($('#grades-part input[type="text"]').length > 0) {
        return $('#unsaved-changes-warning').text();
    }
};
