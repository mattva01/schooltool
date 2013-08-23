#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for schooltool.common
"""

import unittest
import doctest
import datetime

from zope.traversing.testing import setUp


class TestHelpers(unittest.TestCase):

    # parse_date has a doctest

    def test_parse_datetime(self):
        from schooltool.common import parse_datetime
        dt = datetime.datetime
        valid_dates = (
            ("2000-01-01 00:00:00", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2000-01-01 00:00:00.000000", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2000-01-01T00:00:00", dt(2000, 1, 1, 0, 0, 0, 0)),
            ("2005-12-23 11:22:33", dt(2005, 12, 23, 11, 22, 33)),
            ("2005-12-23T11:22:33", dt(2005, 12, 23, 11, 22, 33)),
            ("2005-12-23T11:22:33.4", dt(2005, 12, 23, 11, 22, 33, 400000)),
            ("2005-12-23T11:22:33.456789", dt(2005, 12, 23, 11, 22, 33,
                                              456789)),
        )
        for s, d in valid_dates:
            result = parse_datetime(s)
            self.assertEquals(result, d,
                              "parse_datetime(%r) returned %r" % (s, result))
        invalid_dates = (
            "2000/01/01",
            "2100-02-29 00:00:00",
            "2005-12-23 11:22:33 "
        )
        for s in invalid_dates:
            try:
                result = parse_datetime(s)
            except ValueError:
                pass
            else:
                self.fail("parse_datetime(%r) did not raise" % s)


def test_suite():
    optionflags = (doctest.ELLIPSIS
                   | doctest.REPORT_NDIFF
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('schooltool.common',
                                       optionflags=optionflags))
    suite.addTest(doctest.DocTestSuite('schooltool.common.inlinept',
                                       optionflags=optionflags,
                                       setUp=lambda test: setUp()))
    suite.addTest(unittest.makeSuite(TestHelpers))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
