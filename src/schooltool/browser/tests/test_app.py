#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Tests for schooltool views.

$Id: test_app.py 3481 2005-04-21 15:28:29Z bskahan $
"""

import unittest

from zope.testing import doctest
from zope.publisher.browser import TestRequest

from schoolbell.app.browser.tests.setup import setUp, tearDown


def doctest_CourseView():
    r"""View for courses.

    Lets create a simple view for a course:

        >>> from schooltool.browser.app import CourseView
        >>> from schooltool.app import Course
        >>> course = Course()
        >>> request = TestRequest()
        >>> view = CourseView(course, request)

    """


def doctest_SectionView():
    r"""View for sections

    Lets create a simple view for a section:

        >>> from schooltool.browser.app import SectionView
        >>> from schooltool.app import Section
        >>> section = Section()
        >>> request = TestRequest()
        >>> view = SectionView(section, request)

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
