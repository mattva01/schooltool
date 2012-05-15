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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Selenium Functional Testing Utilities for course.
"""
import os

from schooltool.testing.selenium import SeleniumLayer

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

course_selenium_layer = SeleniumLayer(filename,
                                      __name__,
                                      'course_selenium_layer')

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
                   title=None, ends=None, **kw):
        optional = (
            'description',
            )
        browser.query.link('School').click()
        browser.query.link('Sections').click()
        browser.query.link(schoolyear).click()
        browser.query.link('Section').click()
        browser.query.id('courses-widgets-course').ui.select_option(course)
        browser.query.id('terms-widgets-starts').ui.select_option(term)
        ends_widget = browser.query.id('terms-widgets-ends')
        if ends is None:
            ends_widget.ui.select_option(term)
        else:
            ends_widget.ui.select_option(ends)
        for name in optional:
            if name in kw:
                value = kw[name]
                widget_id = ''.join(['form-widgets-', name])
                browser.query.id(widget_id).ui.set_value(value)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)
        if title is not None:
            page = browser.query.tag('html')
            browser.query.xpath('//a[@title="Edit this section"]').click()
            browser.wait(lambda: page.expired)
            title_widget = browser.query.id('form-widgets-title')
            title_widget.clear()
            title_widget.type(title)
            page = browser.query.tag('html')
            browser.query.button('Submit').click()
            browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.add', addSection))

    def addInstructors(browser, schoolyear, term, section, instructors):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit instructors for this section"]'
        browser.query.xpath(selector).click()
        selector = 'available_table-ajax-available_table--title'
        browser.query.id(selector).type(', '.join(instructors))
        selector = '#available_table-ajax-available_table- table'
        table = browser.query.css(selector)
        browser.query.name('SEARCH_BUTTON').click()
        browser.wait(lambda: table.expired)
        # XXX: Click Show All here in case there are lots of people
        selector = '#available_table-ajax-available_table- table'
        table = browser.query.css(selector)
        browser.query.name('ADD_DISPLAYED_RESULTS').click()
        browser.wait(lambda: table.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.instructors.add', addInstructors))

    def removeInstructors(browser, schoolyear, term, section, instructors):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit instructors for this section"]'
        browser.query.xpath(selector).click()
        # XXX: Click Show All here in case there are lots of people
        for instructor in instructors:
            selector = '#current_table-ajax-current_table- table'
            table = browser.query.css(selector)
            selector = '//button[@name="remove_item.%s"]' % instructor
            browser.query.xpath(selector).click()
            browser.wait(lambda: table.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.instructors.remove', removeInstructors))

    def addStudents(browser, schoolyear, term, section, students):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit students for this section"]'
        browser.query.xpath(selector).click()
        selector = 'available_table-ajax-available_table--title'
        browser.query.id(selector).type(', '.join(students))
        selector = '#available_table-ajax-available_table- table'
        table = browser.query.css(selector)
        browser.query.name('SEARCH_BUTTON').click()
        browser.wait(lambda: table.expired)
        # XXX: Click Show All here in case there are lots of people
        table = browser.query.tag('table')
        browser.query.name('ADD_DISPLAYED_RESULTS').click()
        browser.wait(lambda: table.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.students.add', addStudents))

    def removeStudents(browser, schoolyear, term, section, students):
        browser.ui.section.go(schoolyear, term, section)
        selector = '//a[@title="Edit students for this section"]'
        browser.query.xpath(selector).click()
        # XXX: Click Show All here in case there are lots of people
        for student in students:
            selector = '#current_table-ajax-current_table- table'
            table = browser.query.css(selector)
            selector = '//button[@name="remove_item.%s"]' % student
            browser.query.xpath(selector).click()
            browser.wait(lambda: table.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'section.students.remove', removeStudents))

    def visitSection(browser, schoolyear, term, section):
        browser.open('http://localhost/sections')
        browser.query.link(schoolyear).click()
        browser.query.id('SEARCH').type(section)
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

registerSeleniumSetup()
del registerSeleniumSetup
