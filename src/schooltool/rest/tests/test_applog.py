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
        self.assertEquals(result, 'y00 h4v3 b33n 0wn3d\n')

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
        self.assertEquals(result, 'fit\nbit\nkite\n')

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
        self.assertEquals(result, '\xc3\xbf\n')  # '\u00ff' in UTF-8


class TestApplicationLogQuery(unittest.TestCase):

    def test(self):
        from schooltool.rest.applog import ApplicationLogQuery
        query = ApplicationLogQuery(StringIO('y00 h4v3 b33n 0wn3d'))
        self.assertEquals(query.result, ['y00 h4v3 b33n 0wn3d'])

    def test_filter(self):
        from schooltool.rest.applog import ApplicationLogQuery
        applog = StringIO("cut\nfit\ndog\nbit\nkite")
        query = ApplicationLogQuery(applog, filter_str="it")
        self.assertEquals(query.result, ["fit", "bit", "kite"])

    def test_filter_unicode(self):
        from schooltool.rest.applog import ApplicationLogQuery
        import schooltool.common

        old_locale_charset = schooltool.common.locale_charset
        schooltool.common.locale_charset = 'latin-1'

        applog = StringIO("assume latin-1\n\xFF\n")
        query = ApplicationLogQuery(applog, filter_str=u'\xFF')
        self.assertEquals(query.result, [u'\xFF'])

        schooltool.common.locale_charset = old_locale_charset

    def test_getPageInRange(self):
        from schooltool.rest.applog import ApplicationLogQuery
        query = ApplicationLogQuery(StringIO("foo"))
        self.assertEquals(query.getPageInRange(1, 10, 100), (1, 10))
        self.assertEquals(query.getPageInRange(2, 10, 100), (2, 10))

        # If the last pagencomplete, slice does the right thing
        self.assertEquals(query.getPageInRange(2, 10, 12), (2, 2))

        # Negative indices counting from the end
        self.assertEquals(query.getPageInRange(-1, 10, 12), (2, 2))
        self.assertEquals(query.getPageInRange(-2, 10, 12), (1, 2))

        # Out of range get last page
        self.assertEquals(query.getPageInRange(3, 10, 12), (2, 2))
        self.assertEquals(query.getPageInRange(-3, 10, 12), (1, 2))

    def testPaging(self):
        from schooltool.rest.applog import ApplicationLogQuery
        applog = StringIO("cut\nfit\ndog\nbit\nkite\n")
        query = ApplicationLogQuery(applog, page=-1, pagesize=2)
        self.assertEquals(query.page, 3)
        self.assertEquals(query.total, 3)
        self.assertEquals(query.result, ['kite'])

    def testCharsetTranscoding(self):
        from schooltool.rest.applog import ApplicationLogQuery
        import schooltool.common

        old_locale_charset = schooltool.common.locale_charset
        schooltool.common.locale_charset = 'latin-1'

        applog = StringIO('\xff')
        query = ApplicationLogQuery(applog, page=-1, pagesize=2)
        self.assertEquals(query.result, [u'\u00ff'])

        schooltool.common.locale_charset = old_locale_charset


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApplicationLogView))
    suite.addTest(unittest.makeSuite(TestApplicationLogQuery))
    return suite

if __name__ == '__main__':
    unittest.main()

