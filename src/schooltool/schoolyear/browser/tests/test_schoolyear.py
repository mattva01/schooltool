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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Tests for School year views
"""
import unittest
from zope.testing import doctest

from schooltool.schoolyear.testing import setUp
from schooltool.schoolyear.testing import tearDown
from schooltool.schoolyear.testing import provideStubUtility
from schooltool.schoolyear.testing import provideStubAdapter

from schooltool.schoolyear.ftesting import schoolyear_functional_layer


def doctest_SchoolYearAbsoluteURLAdapter():
    """TODO"""


def doctest_SchoolYearAddFormAdapter():
    """TODO"""


def doctest_SchoolYearAddView():
    """TODO"""


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = schoolyear_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
