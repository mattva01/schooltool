#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Functional Testing Utilities for basic person

$Id$
"""
import os

from schooltool.skin.skin import ISchoolToolSkin
from schooltool.testing.functional import ZCMLLayer
from schooltool.basicperson.browser.skin import IBasicPersonLayer


class IBasicPersonFtestingSkin(IBasicPersonLayer, ISchoolToolSkin):
    """Skin for Basic Person functional tests."""


dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'ftesting.zcml')

basicperson_functional_layer = ZCMLLayer(filename,
                                  __name__,
                                  'basicperson_functional_layer')


def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium

    def addPerson(browser, first_name, last_name, username, password):
        browser.query.link('School').click()
        browser.query.link('People').click()
        browser.query.link('Person').click()
        browser.query.name('form.widgets.first_name').type(first_name)
        browser.query.name('form.widgets.last_name').type(last_name)
        browser.query.name('form.widgets.username').type(username)
        browser.query.name('form.widgets.password').type(password)
        browser.query.name('form.widgets.confirm').type(password)
        page = browser.query.tag('html')
        browser.query.button('Submit').click()
        browser.wait(lambda: page.expired)

    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerBrowserUI(
            'person.add', addPerson))

registerSeleniumSetup()
del registerSeleniumSetup
