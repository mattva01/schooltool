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
Unit tests for schooltool.rest.applog

$Id$
"""

import unittest
from StringIO import StringIO
from schooltool.rest.tests import RequestStub

__metaclass__ = type


class TestApplicationLogView(unittest.TestCase):

    def setUp(self):
        import schooltool.common
        from schooltool.rest.applog import ApplicationLogView
        self.old_locale_charset = schooltool.common.locale_charset
        self.view = ApplicationLogView(None)
        self.view.authorization = lambda ctx, rq: True
        self.view.openLog = lambda f: StringIO('y00 h4v3 b33n 0wn3d')
        self.request = RequestStub()
        class SiteStub:
            applog_path = 'whatever'
        self.request.site = SiteStub()

    def tearDown(self):
        import schooltool.common
        schooltool.common.locale_charset = self.old_locale_charset

    def test(self):
        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, 'y00 h4v3 b33n 0wn3d')

        self.request.site.applog_path = None
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

    def testFilter(self):
        self.view.openLog = lambda f: StringIO("cut\nfit\ndog\nbit\nkite")
        self.request.args.update({'filter': ['i']})

        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, 'fit\nbit\nkite')

    def testFilterUnicode(self):
        import schooltool.common
        schooltool.common.locale_charset = 'latin-1'
        self.view.openLog = lambda f: StringIO("assume latin-1\n\xFF\n")
        self.request.args.update({'filter': ['\xC3\xBF']})

        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, '\xC3\xBF\n')

    def testPaging(self):
        self.view.openLog = lambda f: StringIO("cut\nfit\ndog\nbit\nkite\n")
        self.request.args.update({'filter': [''],
                                  'pagesize': ["2"], 'page': ["-1"]})

        result = self.view.render(self.request)

        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(self.request.headers['x-page'], "3")
        self.assertEquals(self.request.headers['x-total-pages'], "3")
        self.assertEquals(result, 'kite\n')

    def test_getPageInRange(self):
        self.assertEquals(self.view.getPageInRange(1, 10, 100), (1, 10))
        self.assertEquals(self.view.getPageInRange(2, 10, 100), (2, 10))

        # If the last page is incomplete, slice does the right thing
        self.assertEquals(self.view.getPageInRange(2, 10, 12), (2, 2))

        # Negative indices mean counting from the end
        self.assertEquals(self.view.getPageInRange(-1, 10, 12), (2, 2))
        self.assertEquals(self.view.getPageInRange(-2, 10, 12), (1, 2))

        # Out of range gets the last page
        self.assertEquals(self.view.getPageInRange(3, 10, 12), (2, 2))
        self.assertEquals(self.view.getPageInRange(-3, 10, 12), (1, 2))

    def testBadPageSize(self):
        self.request.args.update({'filter': [''],
                                  'pagesize': ["0"], 'page': ["1"]})
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

        self.request.code = 200
        self.request.args.update({'filter': [''],
                                  'pagesize': ["-2"], 'page': ["1"]})
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

    def testErrorNonInt(self):
        self.request.args.update({'pagesize': ["1"], 'page': ["one"]})
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

        self.request.code = 200
        self.request.args.update({'pagesize': ["two"], 'page': ["1"]})
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 400)

    def testCharsetTranscoding(self):
        import schooltool.common
        schooltool.common.locale_charset = 'latin-1'
        self.view.openLog = lambda f: StringIO('\xff')
        result = self.view.render(self.request)
        self.assertEquals(self.request.code, 200)
        self.assertEquals(self.request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assertEquals(result, '\xc3\xbf')  # '\u00ff' in UTF-8


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplicationLogView))
    return suite

if __name__ == '__main__':
    unittest.main()

