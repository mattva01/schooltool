test('setNotEdited', function() {
    window.edited = true;
    setNotEdited();
    equal(window.edited, false);
});

test('setEdited', function() {
    window.edited = false;
    setEdited();
    equal(window.edited, true);
});

test('checkChanges edited=false', function() {
    window.edited = false;
    window.saveFlag = null;
    var result = checkChanges();
    equal(window.saveFlag, null);
    equal(result, null);
});

test('checkChanges edited=true confirm=true', function() {
    window.button_was_clicked = false;
    $('#main').append('<input type="button" name="UPDATE_SUBMIT" />');
    $('#main input[name="UPDATE_SUBMIT"]').click(function() {
        window.button_was_clicked = true;
    });
    window.edited = true;
    window.saveFlag = null;
    window.warningText = 'warning!!!';
    window.confirm = function(text) {
        return true;
    };
    var result = checkChanges();
    equal(window.saveFlag, true);
    equal(window.button_was_clicked, true);
    equal(result, null);
    $('#main').empty();
});

test('checkChanges edited=true confirm=false', function() {
    window.edited = true;
    window.saveFlag = null;
    window.warningText = 'warning!!!';
    window.confirm = function(text) {
        return false;
    };
    var result = checkChanges();
    equal(window.saveFlag, false);
    equal(result, true);
});

test('removeInput', function() {
    var td = $('<td original="90"><input type="text" value="100" /></td>');
    equal(td.attr('original'), '90');
    equal(td.text(), '');
    removeInput(td);
    equal(td.attr('original'), undefined);
    equal(td.text(), '90');
});

test('buildURL', function() {
    var base_url = 'http://example.org/1/2';
    var view = 'myview.html';
    equal(buildURL(base_url, view), 'http://example.org/1/2/myview.html');
});

test('hidePopup', function() {
    var form = $('<div><ul class="popup_active"><li>item</li></ul></div>');
    $('#main').append(form);
    equal(form.find('ul').is(':hidden'), false);
    equal(form.find('.popup_active').length, 1);
    hidePopup(form);
    equal(form.find('ul').is(':hidden'), true);
    equal(form.find('.popup_active').length, 0);
    $('#main').empty();
});

test('insertPopupMenu', function() {
    var td = $('<td><a href="#">link</a></td>');
    var link = td.find('a');
    insertPopupMenu(link);
    equal(td.find('ul').children().length, 1);
    var img = td.find('ul').find('li').find('img');
    equal(img.attr('src'), 'spinner.gif');
});

test('findColumnHeader', function() {
    var grades = $('<div id="grades-part"></div>');
    var table = $([
        '<table>',
        '  <thead>',
        '    <tr><th id="1">A</th><th id="2">B</th><th id="3">C</th></tr>',
        '  </thead>',
        '  <tbody>',
        '    <tr><td>a1</td><td>b1</td><td>c1</td></tr>',
        '    <tr><td>a2</td><td>b2</td><td>c2</td></tr>',
        '    <tr><td>a3</td><td>b3</td><td>c3</td></tr>',
        '  </tbody>',
        '</table>'].join()
    );
    grades.append(table);
    $('#main').append(grades);
    var a3 = grades.find('tbody').find('tr').eq(2).find('td').eq(0);
    var b1 = grades.find('tbody').find('tr').eq(0).find('td').eq(1);
    var b2 = grades.find('tbody').find('tr').eq(1).find('td').eq(1);
    var c3 = grades.find('tbody').find('tr').eq(2).find('td').eq(2);
    equal(a3.text(), 'a3');
    equal(b1.text(), 'b1');
    equal(b2.text(), 'b2');
    equal(c3.text(), 'c3');
    equal(findColumnHeader(a3).text(), 'A');
    equal(findColumnHeader(b1).text(), 'B');
    equal(findColumnHeader(b2).text(), 'B');
    equal(findColumnHeader(c3).text(), 'C');
    $('#main').empty();
});

test('findRowHeader', function() {
    var students = $('<div id="students-part"></div>');
    var students_table = $([
        '<table>',
        '  <thead>',
        '    <tr><th>Name</th></tr>',
        '  </thead>',
        '  <tbody>',
        '    <tr><td>N1</td></tr>',
        '    <tr><td>N2</td></tr>',
        '    <tr><td>N3</td></tr>',
        '  </tbody>',
        '</table>'].join()
    );
    students.append(students_table);
    var grades = $('<div id="grades-part"></div>');
    var grades_table = $([
        '<table>',
        '  <thead>',
        '    <tr><th id="1">A</th><th id="2">B</th><th id="3">C</th></tr>',
        '  </thead>',
        '  <tbody>',
        '    <tr><td>a1</td><td>b1</td><td>c1</td></tr>',
        '    <tr><td>a2</td><td>b2</td><td>c2</td></tr>',
        '    <tr><td>a3</td><td>b3</td><td>c3</td></tr>',
        '  </tbody>',
        '</table>'].join()
    );
    grades.append(grades_table);
    $('#main').append(students, grades);
    var a3 = grades.find('tbody').find('tr').eq(2).find('td').eq(0);
    var b1 = grades.find('tbody').find('tr').eq(0).find('td').eq(1);
    var b2 = grades.find('tbody').find('tr').eq(1).find('td').eq(1);
    var c3 = grades.find('tbody').find('tr').eq(2).find('td').eq(2);
    equal(a3.text(), 'a3');
    equal(b1.text(), 'b1');
    equal(b2.text(), 'b2');
    equal(c3.text(), 'c3');
    equal(findRowHeader(a3).text(), 'N3');
    equal(findRowHeader(b1).text(), 'N1');
    equal(findRowHeader(b2).text(), 'N2');
    equal(findRowHeader(c3).text(), 'N3');
    $('#main').empty();
});

test('isScorable', function() {
    var grades = $('<div id="grades-part"></div>');
    var table = $([
        '<table>',
        '  <thead>',
        '    <tr>',
        '      <th class="scorable">A</th>',
        '      <th>B</th>',
        '      <th class="scorable">C</th>',
        '    </tr>',
        '  </thead>',
        '  <tbody>',
        '    <tr><td>a1</td><td>b1</td><td>c1</td></tr>',
        '    <tr><td>a2</td><td>b2</td><td>c2</td></tr>',
        '    <tr><td>a3</td><td>b3</td><td>c3</td></tr>',
        '  </tbody>',
        '</table>'].join()
    );
    grades.append(table);
    $('#main').append(grades);
    var a3 = grades.find('tbody').find('tr').eq(2).find('td').eq(0);
    var b1 = grades.find('tbody').find('tr').eq(0).find('td').eq(1);
    var b2 = grades.find('tbody').find('tr').eq(1).find('td').eq(1);
    var c3 = grades.find('tbody').find('tr').eq(2).find('td').eq(2);
    equal(a3.text(), 'a3');
    equal(b1.text(), 'b1');
    equal(b2.text(), 'b2');
    equal(c3.text(), 'c3');
    equal(isScorable(a3), true);
    equal(isScorable(b1), false);
    equal(isScorable(b2), false);
    equal(isScorable(c3), true);
    $('#main').empty();
});

test('cellInputName', function() {
    var students = $('<div id="students-part"></div>');
    var students_table = $([
        '<table>',
        '  <thead>',
        '    <tr><th>Name</th></tr>',
        '  </thead>',
        '  <tbody>',
        '    <tr><td id="n1">N1</td></tr>',
        '    <tr><td id="n2">N2</td></tr>',
        '    <tr><td id="n3">N3</td></tr>',
        '  </tbody>',
        '</table>'].join()
    );
    students.append(students_table);
    var grades = $('<div id="grades-part"></div>');
    var grades_table = $([
        '<table>',
        '  <thead>',
        '    <tr><th id="1">A</th><th id="2">B</th><th id="3">C</th></tr>',
        '  </thead>',
        '  <tbody>',
        '    <tr><td>a1</td><td>b1</td><td>c1</td></tr>',
        '    <tr><td>a2</td><td>b2</td><td>c2</td></tr>',
        '    <tr><td>a3</td><td>b3</td><td>c3</td></tr>',
        '  </tbody>',
        '</table>'].join()
    );
    grades.append(grades_table);
    $('#main').append(students, grades);
    var a3 = grades.find('tbody').find('tr').eq(2).find('td').eq(0);
    var b1 = grades.find('tbody').find('tr').eq(0).find('td').eq(1);
    var b2 = grades.find('tbody').find('tr').eq(1).find('td').eq(1);
    var c3 = grades.find('tbody').find('tr').eq(2).find('td').eq(2);
    equal(a3.text(), 'a3');
    equal(b1.text(), 'b1');
    equal(b2.text(), 'b2');
    equal(c3.text(), 'c3');
    equal(cellInputName(a3), '1_n3');
    equal(cellInputName(b1), '2_n1');
    equal(cellInputName(b2), '2_n2');
    equal(cellInputName(c3), '3_n3');
    $('#main').empty();
});

test('getInput', function() {
    var students = $('<div id="students-part"></div>');
    var students_table = $([
      '<table>',
      '  <thead>',
      '    <tr><th>Name</th></tr>',
      '  </thead>',
      '  <tbody>',
      '    <tr><td id="n1">N1</td></tr>',
      '    <tr><td id="n2">N2</td></tr>',
      '    <tr><td id="n3">N3</td></tr>',
      '  </tbody>',
      '</table>'].join('')
    );
    students.append(students_table);
    var grades = $('<div id="grades-part"></div>');
    var grades_table = $([
      '<table>',
      '  <thead>',
      '    <tr>',
      '      <th id="1">A</th><th id="2">B</th><th id="3">C</th>',
      '    </tr>',
      '  </thead>',
      '  <tbody>',
      '    <tr>',
      '      <td></td>',
      '      <td><input type="text" value="b1" name="b1" /></td>',
      '      <td>c1</td>',
      '    </tr>',
      '    <tr>',
      '      <td></td>',
      '      <td>b2</td>',
      '      <td>c2</td>',
      '    </tr>',
      '    <tr>',
      '      <td original="Y"><input type="text" value="a3" name="a3" /></td>',
      '      <td>b3</td>',
      '      <td></td>',
      '    </tr>',
      '  </tbody>',
      '</table>'].join()
    );
    grades.append(grades_table);
    $('#main').append(students, grades);
    var a3 = grades.find('tbody').find('tr').eq(2).find('td').eq(0);
    var b1 = grades.find('tbody').find('tr').eq(0).find('td').eq(1);
    var b2 = grades.find('tbody').find('tr').eq(1).find('td').eq(1);
    var c3 = grades.find('tbody').find('tr').eq(2).find('td').eq(2);
    equal(a3.find('input').length, 1);
    equal(a3.find('input').attr('name'), 'a3');
    equal(a3.find('input').attr('value'), 'a3');
    equal(a3.attr('original'), 'Y');
    equal(b1.find('input').length, 1);
    equal(b1.find('input').attr('name'), 'b1');
    equal(b1.find('input').attr('value'), 'b1');
    equal(b1.attr('original'), undefined);
    equal(b2.find('input').length, 0);
    equal(b2.attr('original'), undefined);
    equal(b2.text(), 'b2');
    equal(c3.find('input').length, 0);
    equal(c3.attr('original'), undefined);
    equal(c3.text(), '');
    getInput(a3);
    getInput(b1);
    getInput(b2);
    getInput(c3);
    equal(a3.find('input').length, 1);
    equal(a3.find('input').attr('name'), 'a3');
    equal(a3.find('input').attr('value'), 'a3');
    equal(a3.attr('original'), 'Y');
    equal(b1.find('input').length, 1);
    equal(b1.find('input').attr('name'), 'b1');
    equal(b1.find('input').attr('value'), 'b1');
    equal(b1.attr('original'), undefined);
    equal(b2.find('input').length, 1);
    equal(b2.find('input').attr('name'), '2_n2');
    equal(b2.find('input').attr('value'), 'b2');
    equal(b2.attr('original'), 'b2');
    equal(b2.text(), '');
    equal(c3.find('input').length, 1);
    equal(c3.find('input').attr('name'), '3_n3');
    equal(c3.find('input').attr('value'), '');
    equal(c3.attr('original'), '');
    equal(c3.text(), '');
    $('#main').empty();
});
