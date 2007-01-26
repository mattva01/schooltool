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
Functional tests for schooltool.demographics.

$Id: ftests.py 6562 2007-01-11 13:05:38Z ignas $
"""

import unittest
import os

from schooltool.testing.functional import collect_ftests
from schooltool.testing.functional import ZCMLLayer
from schooltool.app.browser.ftests.setup import logInManager

def addPerson(name, username=None, password=None, groups=None, browser=None):
    """Add a demographics person.

    If username is not specified, it will be taken to be name.lower().

    If password is not specified, it will be taken to be username + 'pwd'.
    """
    if not username:
        username = name.lower()
    if not password:
        password = username + 'pwd'
    if browser is None:
        browser = logInManager()
    browser.getLink('Persons').click()
    browser.getLink('New Person').click()
    browser.getControl('Full name').value = name
    browser.getControl('First name').value = name
    # XXX Last name is a required field defined by demographics
    browser.getControl('Last name').value = 'Fake'
    browser.getControl('Username').value = username
    browser.getControl('Password').value = password
    browser.getControl('Confirm').value = password
    browser.getControl('Add').click()

    if groups:
        browser.getLink('schooldata').click()
        browser.getLink('edit groups').click()
        for group in groups:
            browser.getControl(name='add_item.%s' % group).value = True
        browser.getControl('Add').click()
    browser.open('http://localhost/persons')

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'ftesting.zcml')

demographics_functional_layer = ZCMLLayer(filename,
                                          __name__,
                                          'demographics_functional_layer')

def test_suite():
    return collect_ftests(layer=demographics_functional_layer)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
