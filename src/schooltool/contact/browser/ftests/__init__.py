#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Functional testing utilites for Contacts.
"""
from schooltool.testing.functional import TestBrowser


def addContact(firstname, lastname, address='', email='', browser=None):

    if browser is None:
        browser = TestBrowser('manager', 'schooltool')

    browser.getLink('Manage').click()
    browser.getLink('Contacts').click()
    browser.getLink('New Contact').click()

    browser.getControl('First name').value = firstname
    browser.getControl('Last name').value = lastname
    browser.getControl('Address line 1').value = address
    browser.getControl('Email').value = email

    browser.getControl('Add').click()
