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
Selenium functional tests setup for schooltool.schoolyear
"""

import os

from schooltool.testing.selenium import SeleniumLayer

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

schoolyear_selenium_layer = SeleniumLayer(filename,
                                          __name__,
                                          'schoolyear_selenium_layer')

def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def addSchoolYear(browser, title, first, last, **kw):
        browser.open('http://localhost/schoolyears')
        browser.query.link('School Year').click()
        browser.query.name('form.widgets.title').type(title)
        browser.query.name('form.widgets.first').ui.enter_date(first)
        browser.query.name('form.widgets.last').ui.enter_date(last)
        for group_id in kw.get('copy_groups', []):
            sel = '//input[@name="groups" and @value="%s"]' % group_id
            browser.query.xpath(sel).click()
        for group_id in kw.get('copy_members', []):
            sel = '//input[@name="members" and @value="%s"]' % group_id
            browser.query.xpath(sel).click()
        if kw.get('copy_courses'):
            browser.query.name('importAllCourses').click()
        if kw.get('copy_timetables'):
            browser.query.name('importAllTimetables').click()
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'schoolyear.add', addSchoolYear))

registerSeleniumSetup()
del registerSeleniumSetup
