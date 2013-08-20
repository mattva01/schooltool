#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
High-level setup functions for functional tests relating to basicperson..
"""

from schooltool.app.browser.ftests.setup import logInManager

def addPerson(firstname, lastname, username=None, password=None, groups=None, browser=None):
    """Add a person.

    If username is not specified, it will be taken to be "<firstname>.<lastname>".lower().

    If password is not specified, it will be taken to be username + 'pwd'.
    """
    if not username:
        username = ('%s.%s' % (firstname, lastname)).lower()
    if not password:
        password = username + 'pwd'
    if browser is None:
        browser = logInManager()
    browser.getLink('Manage').click()
    browser.getLink('Persons').click()
    browser.getLink('New Person').click()

    browser.getControl('First name').value = firstname
    browser.getControl('Last name').value = lastname
    browser.getControl('Username').value = username
    browser.getControl('Password').value = password
    browser.getControl('Confirm').value = password
    browser.getControl('Add').click()

    if groups:
        browser.open('http://localhost/persons/%s' % username)
        browser.getLink('edit groups').click()
        for group in groups:
            browser.getControl(name='add_item.%s' % group).value = True
        browser.getControl('Add').click()
    browser.open('http://localhost/persons')
