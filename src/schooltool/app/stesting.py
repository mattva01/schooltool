#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Selenium functional tests setup for gradebook functionality
"""

from itertools import groupby

from schooltool.app.testing import format_table
from schooltool.testing.selenium import WebElement


css_to_code = {
    'valid': 'v',
    'error': 'i',
    'extracredit': 'e',
    }


def tertiary_navigation(browser):
    driver = browser.driver
    result = []
    sel = 'ul.third-nav li'
    for tab in driver.execute_script('return $(arguments[0])', sel):
        link = driver.execute_script('return $(arguments[0]).find("a")', tab)
        text = link[0].get_attribute('title').strip()
        css_class = tab.get_attribute('class')
        if css_class is not None and 'active' in css_class:
            text = '*%s*' % text
        result.append(text)
    return result


def table_header(browser):
    result = []
    row1 = []
    sel = '.students thead a.popup_link'
    for header in browser.driver.execute_script('return $(arguments[0])', sel):
        row1.append(header.text.strip())
    sel = '.grades thead a.popup_link'
    headers = browser.driver.execute_script(
        'return $(arguments[0])', sel)
    row1.extend([header.text.strip() for header in headers])
    sel = '.totals thead a.popup_link'
    headers = browser.driver.execute_script(
        'return $(arguments[0])', sel)
    row1.extend([header.text.strip() for header in headers])
    result.append(row1)
    row2 = ['', '']
    sel = '#grades-part thead tr:nth-child(2) th'
    headers = browser.driver.execute_script(
        'return $(arguments[0])', sel)
    row2.extend([header.text.strip() for header in headers])
    sel = '#totals-part thead th'
    headers = browser.driver.execute_script(
        'return $(arguments[0])', sel)
    row2.extend(['' for header in headers])
    result.append(row2)
    return result


def group_double_rows(rows):
    result = []
    indexes = []
    keep_index = False
    for index, row in enumerate(rows):
        if 'double-' not in row.get_attribute('class'):
            indexes.append((index, row))
        else:
            if not keep_index:
                indexes.append((index, row))
                keep_index = True
            else:
                indexes.append((index-1, row))
                keep_index = False
    for key, iterator in groupby(indexes, lambda (i, row): i):
        group = []
        for j, row in iterator:
            group.append(row)
        result.append(group)
    return result


def get_grades(browser, row, show_validation):
    result = []
    tds = browser.driver.execute_script(
        'return $(arguments[0]).find("td").not(".placeholder")', row)
    for td in tds:
        fields = browser.driver.execute_script(
            'return $(arguments[0]).find("input")', td)
        if fields:
            field = fields[0]
            value = browser.driver.execute_script(
                'return arguments[0].value', field)
            value = '[%s]' % value.ljust(5, '_')
            if show_validation:
                css_class = field.get_attribute('class')
                value += css_to_code.get(css_class, '')
        else:
            value = td.text.strip()
        result.append(value)
    return result


def table_rows(browser, show_validation, hide_homeroom):
    rows = []
    sel = '.students tbody tr'
    student_rows = browser.driver.execute_script(
        'return $(arguments[0])', sel)
    for row in student_rows:
        student = []
        links = browser.driver.execute_script(
            'return $(arguments[0]).find("a.popup_link")', row)
        for link in links:
            student.append(link.text.strip())
        rows.append(student)
    sel = '.totals tbody tr'
    total_rows = browser.driver.execute_script(
        'return $(arguments[0])', sel)
    for index, row in enumerate(total_rows):
        student = rows[index]
        tds = browser.driver.execute_script(
            'return $(arguments[0]).find("td")', row)
        for td in tds:
            student.append(td.text.strip())
    sel = '.grades tbody tr'
    grade_row_groups = group_double_rows(browser.driver.execute_script(
        'return $(arguments[0])', sel))
    student_index = 0
    for row_group in grade_row_groups:
        if len(row_group) > 1 and hide_homeroom:
            row_group = [row_group[-1]]
        for index, row in enumerate(row_group):
            grades = get_grades(browser, row, show_validation)
            if index == 0:
                student_row = rows[student_index]
                rows[student_index] = student_row[:2] + grades + student_row[2:]
            else:
                totals_count = len(student) - 2
                new_row = ['', ''] + grades + ([''] * totals_count)
                rows.insert(student_index, new_row)
            student_index += 1
    return rows


def print_gradebook(browser, show_validation, hide_homeroom):
    nav = tertiary_navigation(browser)
    if nav:
        print format_table([nav])
    rows = []
    rows.extend(table_header(browser))
    for row in table_rows(browser, show_validation, hide_homeroom):
        rows.append(row)
    print format_table(rows, header_rows=2)


def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def printGradebook(browser, show_validation=False, hide_homeroom=False):
        print_gradebook(browser, show_validation, hide_homeroom)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'gradebook.worksheet.pprint', printGradebook))

    def score(browser, student, activity, grade):
        driver = browser.driver
        row_index = None
        column_index = None
        sel = '.students tbody td:first-child a.popup_link'

        # XXX: reverse in tests
        if ', ' in student:
            student = ' '.join(reversed(student.split(', ')))

        for index, link in enumerate(driver.execute_script(
                'return $(arguments[0])', sel)):
            if student == link.get_attribute('title'):
                row_index = index
                break
        sel = '.grades thead a.popup_link'
        for index, link in enumerate(driver.execute_script(
                'return $(arguments[0])', sel)):
            if activity == link.text:
                column_index = index
                break
        sel = '.grades tbody tr'
        grade_row_groups = group_double_rows(browser.driver.execute_script(
            'return $(arguments[0])', sel))
        row = grade_row_groups[row_index][-1]
        sel = 'td:nth-child(%d)' % (column_index + 1)
        raw_cell = driver.execute_script('return $(arguments[0]).find(arguments[1])', row, sel)[0]
        cell = WebElement(raw_cell)
        cell.click()
        sel = '.ui-dialog:visible'
        if not driver.execute_script('return $(arguments[0])', sel):
            cell.query.tag('input').type(browser.keys.DELETE, grade)
            sel = 'ul.ui-autocomplete'
            driver.execute_script(
                '$(arguments[0]).find(arguments[1]).hide()', cell, sel)
        else:
            driver.execute_script(
                'CKEDITOR.instances["form-widgets-value"].setData(arguments[0])', grade)
            browser.query.css('.comment-cell-submit').click()

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'gradebook.worksheet.score', score))

registerSeleniumSetup()
del registerSeleniumSetup
