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
Unit tests for schooltool.views.applog

$Id$
"""

import unittest
from schooltool.views.tests import RequestStub

__metaclass__ = type


class TestApplicationLogView(unittest.TestCase):

    def test(self):
        from schooltool.views.applog import ApplicationLogView
        view = ApplicationLogView(None)
        view.authorization = lambda ctx, rq: True
        view.file_contents = lambda f: 'y00 h4v3 b33n 0wn3d'
        request = RequestStub()
        class SiteStub: applog_path = 'whatever'
        request.site = SiteStub()
        result = view.render(request)

        self.assertEquals(request.code, 200)
        self.assertEquals(request.headers['content-type'], "text/plain")
        self.assertEquals(result, 'y00 h4v3 b33n 0wn3d')

        request.site.applog_path = None
        result = view.render(request)
        self.assertEquals(request.code, 400)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplicationLogView))
    return suite

if __name__ == '__main__':
    unittest.main()

