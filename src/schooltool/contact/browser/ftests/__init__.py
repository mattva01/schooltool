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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Functional testing utilites for Contacts.
"""
from schooltool.testing.functional import TestBrowser
from schooltool.app.browser.ftests.setup import logInManager
from schooltool.email.mail import EmailUtility


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


def addPerson(name, username=None, password=None, groups=None, browser=None):
    """Add a person.

    If username is not specified, it will be taken to be name.lower().

    If password is not specified, it will be taken to be username + 'pwd'.
    """
    if not username:
        username = name.lower()
    if not password:
        password = username + 'pwd'
    if browser is None:
        browser = logInManager()
    browser.getLink('Manage').click()
    browser.getLink('Persons').click()
    browser.getLink('New Person').click()
    split_name = name.split(' ', 1)
    first_name = split_name.pop(0)
    last_name = split_name and split_name.pop() or name
    browser.getControl('First name').value = first_name
    browser.getControl('Last name').value = last_name
    browser.getControl('Username').value = username
    browser.getControl('Password').value = password
    browser.getControl('Confirm').value = password
    browser.getControl('Add').click()


class StubEmailUtility(EmailUtility):

    def send(self, email):
        print "Email from %s sent to %s" % (email.from_address,
                                            ''.join(email.to_addresses))
        return True
