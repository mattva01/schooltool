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
Unit tests for schooltool.browser.applog

$Id$
"""

import unittest
from StringIO import StringIO

from schooltool.browser.tests import RequestStub

__metaclass__ = type

class TestAppLog(unittest.TestCase):

    def setUp(self):
        from schooltool.browser.applog import ApplicationLogView
        self.view = ApplicationLogView(None)
        self.view.authorization = lambda x, y: True
        self.view.openLog = lambda fn: StringIO("defaced\nby\nevil\nhackers")

        class SiteStub:
            applog_path = 'anywhere'

        self.request = RequestStub()
        self.request.site = SiteStub()

    def test(self):
        contents = self.view.render(self.request)
        self.assert_("Application log" in contents)
        self.assert_("defaced" in contents)
        self.assert_("hackers" in contents)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAppLog))
    return suite


if __name__ == '__main__':
    unittest.main()
