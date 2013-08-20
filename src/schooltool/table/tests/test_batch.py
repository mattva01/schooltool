#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
"""Batch tests
"""
import unittest
import doctest

from zope.publisher.browser import TestRequest


class FormatterStub(object):
    def extra_url(self):
        return ""


def doctest_Batch_needsBatch():
    """Tests for needsBatch property

    Let's create a Batch

        >>> from schooltool.table.batch import Batch
        >>> formatter = FormatterStub()
        >>> formatter.request = TestRequest()
        >>> formatter._items = []
        >>> formatter.prefix = "persons"
        >>> batch = Batch(formatter)

     If there are no items - we don't need batching:

        >>> batch.needsBatch
        False

     If we have more items than the size of the page we will show
     batching controls:

        >>> batch.full_size = 29
        >>> batch.start = 0
        >>> batch.needsBatch
        True

     Now if we go to the next page, we should still see batching:

        >>> batch.start = 25
        >>> batch.needsBatch
        True

     Though if we only have as many items as the page size - we should
     see no batching:

        >>> batch.full_size = 25
        >>> batch.start = 0
        >>> batch.needsBatch
        False

    Unless we somehow paged less than the page size items forward:

        >>> batch.full_size = 25
        >>> batch.start = 10
        >>> batch.needsBatch
        True

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
