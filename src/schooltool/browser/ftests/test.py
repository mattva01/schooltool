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


class URLOpener(urllib.URLopener):

    def http_error(self, url, fp, errcode, errmsg, headers, data=None):
        """Default error handling -- don't raise an exception."""
        fp = urllib.addinfourl(fp, headers, "http:" + url)
        fp.status = errcode
        fp.message = errmsg
        return fp

    def open_http(self, url, data=None):
        fp = urllib.URLopener.open_http(self, url, data)
        if not hasattr(fp, 'status'):
            fp.status = 200
            fp.message = 'OK'
        return fp


class Browser(object):
    """Class emulating a web browser.

    The emulation is not very complete.  HTTP redirects (only code 302)
    are processed.  There is some very crude basic support for cookies.

    Attributes:

        url         URL of the current page.
        content     content of the current page.
        status      HTTP status code.
        message     HTTP status message.
        headers     a mimelib.Message containing HTTP response headers.

    """

    def __init__(self):
        self.url = None
        self.content = None
        self._cookies = {}

    def go(self, url):
        """Go to a specified URL."""
        self._open(url)

    def post(self, url, form):
        """Post a form to a specified URL."""
        self._open(url, urllib.urlencode(form))

    def _open(self, url, data=None):
        self.url = url
        opener = URLOpener()
        for name, value in self._cookies.items():
            # Quick and dirty hack
            opener.addheader('Cookie', '%s=%s' % (name, value))
        fp = opener.open(url, data=data)
        self.content = fp.read()
        self.headers = fp.info()
        self.status = fp.status
        self.message = fp.message
        fp.close()
        for cookie in self.headers.getheaders('Set-Cookie'):
            # Quick and dirty hack
            args = cookie.split(';')
            name, value = args[0].split('=')
            self._cookies[name] = value
        if self.status == 302:
            # Process HTTP redirects.
            location = self.headers.get('Location')
            # This might loop.  Let's hope it doesn't
            self._open(location)


class TestLogin(unittest.TestCase):

    def test(self):
        browser = Browser()
        browser.go('http://localhost:8814/')
        self.assert_('Welcome' in browser.content)
        self.assert_('Username' in browser.content)

        browser.post('http://localhost:8814/',
                     {'username': 'manager', 'password': 'schooltool'})
        self.assertEquals(browser.url, 'http://localhost:8814/persons/manager')
        self.assert_('Person info' in browser.content)


class TestPersonEdit(unittest.TestCase):

    def test(self):
        browser = Browser()
        browser.post('http://localhost:8814/',
                     {'username': 'manager', 'password': 'schooltool'})
        browser.go('http://localhost:8814/persons/manager/edit.html')
        self.assert_('Edit person info' in browser.content)

        browser.post('http://localhost:8814/persons/manager/edit.html',
                     {'first_name': 'xyzzy', 'last_name': 'foobar',
                      'comment': 'I can write!'})
        self.assertEquals(browser.url, 'http://localhost:8814/persons/manager')
        self.assert_('xyzzy' in browser.content)
        self.assert_('foobar' in browser.content)
        self.assert_('I can write!' in browser.content)

        browser.go('http://localhost:8814/persons/manager/edit.html')
        self.assert_('xyzzy' in browser.content)
        self.assert_('foobar' in browser.content)
        self.assert_('I can write!' in browser.content)

        # Restore original person info
        browser.post('http://localhost:8814/persons/manager/edit.html',
                     {'first_name': 'Manager', 'last_name': '', 'comment': ''})


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLogin))
    suite.addTest(unittest.makeSuite(TestPersonEdit))
    return suite


if __name__ == '__main__':
    unittest.main()
