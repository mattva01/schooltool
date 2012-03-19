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
Selenium Functional Testing Utilities for groups.
"""

import os

from schooltool.testing.selenium import SeleniumLayer

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

    def addMembers(browser, schoolyear, group, members):
        browser.ui.group.go(schoolyear, group)
        selector = '//a[@title="Edit members for this group"]'
        browser.query.xpath(selector).click()
        selector = 'available_table-ajax-available_table--title'
        browser.query.id(selector).type(', '.join(members))
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
            'group.members.add', addMembers))

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
