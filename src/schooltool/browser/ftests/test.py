#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Functional tests for SchoolTool web application
"""

import unittest
import urllib

from schooltool.ftests import setup
from schooltool.browser.ftests import Browser


#
# Tests
#

class TestLogin(setup.TestCase):

    def test(self):
        self.do_test(self.web_server)

    def test_ssl(self):
        self.do_test(self.web_server_ssl)

    def do_test(self, site):
        browser = Browser()
        browser.go(site)
        self.assert_('Welcome' in browser.content)
        self.assert_('Username' in browser.content)

        browser.post(site, {'username': 'manager', 'password': 'schooltool'})
        self.assertEquals(browser.url, site + '/start')
        self.assert_('Start' in browser.content)
        link_to_password_form = site + '/persons/manager/password.html'
        self.assert_(link_to_password_form in browser.content)


class TestPersonEdit(setup.TestCase):

    def test(self):
        browser = Browser()
        browser.post('http://localhost:8814/',
                     {'username': 'manager', 'password': 'schooltool'})
        browser.go('http://localhost:8814/persons/manager/edit.html')
        self.assert_('Edit person info' in browser.content)

        browser.post('http://localhost:8814/persons/manager/edit.html',
                     {'first_name': 'xyzzy \xc4\x85', 'last_name': 'foobar',
                      'date_of_birth': '2004-08-04',
                      'comment': 'I can write!', 'photo': ''})
        self.assertEquals(browser.url, 'http://localhost:8814/persons/manager')
        self.assert_('xyzzy \xc4\x85' in browser.content)
        self.assert_('foobar' in browser.content)
        self.assert_('I can write!' in browser.content)

        browser.go('http://localhost:8814/persons/manager/edit.html')
        self.assert_('xyzzy' in browser.content)
        self.assert_('foobar' in browser.content)
        self.assert_('I can write!' in browser.content)

        browser.post('http://localhost:8814/persons/manager/edit.html',
                     {'first_name': 'Manager', 'last_name': '',
                      'date_of_birth': '2004-08-04',
                      'comment': '', 'photo': ''})
        self.assert_('field is required'in browser.content)


class TestResetDB(setup.TestCase):

    def test(self):
        # Log in
        browser = Browser()
        browser.post('http://localhost:8814/',
                     {'username': 'manager', 'password': 'schooltool'})

        # Change something in the database
        browser.post('http://localhost:8814/persons/manager/edit.html',
                     {'first_name': 'Test', 'last_name': 'Test'})
        browser.go('http://localhost:8814/persons/manager/edit.html')
        self.assert_('Manager' not in browser.content)

        # Reset the database
        browser.go('http://localhost:8814/reset_db.html')
        self.assert_('Warning' in browser.content)
        browser.post('http://localhost:8814/reset_db.html',
                     {'confirm': 'Confirm'})

        # Log in
        browser.post('http://localhost:8814/',
                     {'username': 'manager', 'password': 'schooltool'})

        # Our changes should have been discarded
        browser.go('http://localhost:8814/persons/manager/edit.html')
        self.assert_('Manager' in browser.content)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLogin))
    suite.addTest(unittest.makeSuite(TestPersonEdit))
    suite.addTest(unittest.makeSuite(TestResetDB))
    return suite


if __name__ == '__main__':
    unittest.main()
