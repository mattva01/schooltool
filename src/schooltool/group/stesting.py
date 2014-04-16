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
Selenium Functional Testing Utilities for groups.
"""

import os

from schooltool.testing.selenium import SeleniumLayer
from schooltool.testing.selenium import add_temporal_relationship
from schooltool.testing.selenium import remove_temporal_relationship

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'stesting.zcml')

group_selenium_layer = SeleniumLayer(filename,
                                     __name__,
                                     'group_selenium_layer')

def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def addGroup(browser, schoolyear, title, **kw):
        optional = (
            'description',
            )
        browser.query.link('School').click()
        browser.query.link('Groups').click()
        browser.query.link(schoolyear).click()
        browser.query.link('Group').click()
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
            'group.add', addGroup))

    def addMembers(browser, schoolyear, group, members,
                   state=None, date=None):
        browser.ui.group.go(schoolyear, group)
        selector = '//a[@title="Edit members for this group"]'
        browser.query.xpath(selector).click()
        add_temporal_relationship(browser, members, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'group.members.add', addMembers))

    def removeMembers(browser, schoolyear, group, members,
                      state=None, date=None):
        browser.ui.group.go(schoolyear, group)
        selector = '//a[@title="Edit members for this group"]'
        browser.query.xpath(selector).click()
        if state is None:
            state = 'Removed' if group != 'Students' else 'Withdrawn'
        remove_temporal_relationship(browser, members, state, date)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'group.members.remove', removeMembers))

    def visitGroup(browser, schoolyear, group):
        browser.open('http://localhost/groups')
        browser.query.link(schoolyear).click()
        browser.query.id('SEARCH').type(group)
        table = browser.query.css('form table')
        browser.query.name('SEARCH_BUTTON').click()
        browser.wait(lambda: table.expired)
        # XXX: Click Show All here in case there are lots of groups
        sel = '//a[text()="%s"]' % group
        page = browser.query.tag('html')
        browser.query.xpath(sel).click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'group.go', visitGroup))

registerSeleniumSetup()
del registerSeleniumSetup
