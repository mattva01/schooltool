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
Unit tests for schooltool.browser.app

$Id$
"""

import unittest

# XXX should schooltool.browser depend on schooltool.views?
from schooltool.views.tests import RequestStub


__metaclass__ = type


class TestAppView(unittest.TestCase):

    def test(self):
        from schooltool.app import Application
        from schooltool.browser.app import LoginPage
        app = Application()
        view = LoginPage(app)
        request = RequestStub()
        view.authorization = lambda ctx, req: True
        result = view.render(request)
        self.assert_('Username' in result)
        self.assertEquals(request.headers['content-type'],
                          "text/html; charset=UTF-8")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppView))
    return suite

if __name__ == '__main__':
    unittest.main()
