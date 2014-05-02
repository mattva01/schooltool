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
Selenium Functional Testing Utilities for course.
"""
import os

from schooltool.app.testing import format_table
from schooltool.testing.selenium import SeleniumLayer
from schooltool.testing.selenium import add_temporal_relationship
from schooltool.testing.selenium import remove_temporal_relationship

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

course_selenium_layer = SeleniumLayer(filename,
                                      __name__,
                                      'course_selenium_layer')


def print_table(table):
    rows = []
    row = []
    for th in table.query_all.css('thead tr th'):
        row.append(th.text)
    rows.append(row)
    for tr in table.query_all.css('tbody tr'):
        row = []
        for td in tr.query_all.tag('td'):
            row.append(td.text)
        rows.append(row)
    print format_table(rows, header_rows=1)


def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def addCourse(browser, schoolyear, title, **kw):
        optional = (
            'description',
            'course_id',
            'government_id',
            'credits',
            'level',
            )
        browser.query.link('School').click()
        browser.query.link('Courses').click()
        browser.query.link(schoolyear).click()
        browser.query.link('Course').click()
        browser.query.name('form.widgets.title').type(title)
        for name in optional:
            if name in kw:
                value = kw[name]
                widget_id = ''.join(['form-widgets-', name])
                browser.query.id(widget_id).ui.set_value(value)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'course.add', addCourse))

    def addSection(browser, schoolyear, term, course,
                   title=None, ends=None, location=None, **kw):
        optional = (
            'description',
            )
        browser.query.link('School').click()
        browser.query.link('Sections').click()
        browser.query.link(schoolyear).click()
        browser.query.link('Section').click()
        if title is not None:
            browser.query.name('form.widgets.title').type(title)
        browser.query.id('courses-widgets-course').ui.select_option(course)
        browser.query.id('terms-widgets-starts').ui.select_option(term)
        ends_widget = browser.query.id('terms-widgets-ends')
        if ends is None:
            ends_widget.ui.select_option(term)
        else:
            ends_widget.ui.select_option(ends)
        if location is not None:
            browser.query.id('location-widgets-location').ui.select_option(
                location)
        for name in optional:
            if name in kw:
                value = kw[name]
                widget_id = ''.join(['form-widgets-', name])
                browser.query.id(widget_id).ui.set_value(value)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)
        redirect = browser.url
        title = browser.query.tag('h2').text
        if 'instructors' in kw:
            browser.ui.section.instructors.add(
                schoolyear, term, title, kw['instructors'],
                kw.get('instructors_state'), kw.get('instructors_date'))
        if 'students' in kw:
            browser.ui.section.students.add(
                schoolyear, term, title, kw['students'],
                kw.get('students_state'), kw.get('students_date'))
        browser.open(redirect)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.add', addSection))

    def addInstructors(browser, schoolyear, term, section, instructors,
                       state=None, date=None):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit instructors for this section"]'
        browser.query.xpath(selector).click()
        add_temporal_relationship(browser, instructors, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.instructors.add', addInstructors))

    def removeInstructors(browser, schoolyear, term, section, instructors,
                          state=None, date=None):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit instructors for this section"]'
        browser.query.xpath(selector).click()
        if state is None:
            state = 'Withdrawn'
        remove_temporal_relationship(browser, instructors, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.instructors.remove', removeInstructors))

    def addStudents(browser, schoolyear, term, section, students,
                    state=None, date=None):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit students for this section"]'
        browser.query.xpath(selector).click()
        add_temporal_relationship(browser, students, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.students.add', addStudents))

    def removeStudents(browser, schoolyear, term, section, students,
                       state=None, date=None):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit students for this section"]'
        browser.query.xpath(selector).click()
        if state is None:
            state = 'Withdrawn'
        remove_temporal_relationship(browser, students, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.students.remove', removeStudents))

    def visitSection(browser, schoolyear, term, section):
        browser.open('http://localhost/sections')
        browser.query.link(schoolyear).click()
        selector = 'input.text-widget'
        browser.query.css(selector).type(section)
        table = browser.query.css('form table')
        browser.query.name('SEARCH_BUTTON').click()
        browser.wait(lambda: table.expired)
        # XXX: Click Show All here in case there are lots of sections
        selector = ('//td[following-sibling::*[contains(text(),"%s")]]'
                    '/a[text()="%s"]') % (term, section)
        page = browser.query.tag('html')
        browser.query.xpath(selector).click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.go', visitSection))

    def printInstructorsTable(browser, schoolyear, term, section):
        browser.ui.section.go(schoolyear, term, section)
        sel = '#section_instruction_person_table-ajax-view-context-instructors-section_instruction_person_table- table.data'
        table = browser.query.css(sel)
        print_table(table)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.instructors.print_table', printInstructorsTable))

    def printStudentsTable(browser, schoolyear, term, section):
        browser.ui.section.go(schoolyear, term, section)
        sel = '#section_membership_person_table-ajax-view-context-members-section_membership_person_table- table.data'
        table = browser.query.css(sel)
        print_table(table)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.students.print_table', printStudentsTable))

registerSeleniumSetup()
del registerSeleniumSetup
