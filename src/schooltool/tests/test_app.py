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
Unit tests for schooltool.app.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app import zapi
from zope.interface.verify import verifyObject


def doctest_SchoolToolApplication():
    """SchoolToolApplication

    Let's check that the interface is satisfied:

        >>> from schooltool.app import SchoolToolApplication
        >>> from schooltool.interfaces import ISchoolToolApplication
        >>> from zope.interface.verify import verifyObject

        >>> app = SchoolToolApplication()
        >>> verifyObject(ISchoolToolApplication, app)
        True

    Also, the app is a schoolbell application:

        >>> from schoolbell.app.interfaces import ISchoolBellApplication
        >>> verifyObject(ISchoolBellApplication, app)
        True

    Make sure the default groups and resources are created

        >>> from schoolbell.app.interfaces import IGroup
        >>> teachers = app['groups']['teachers']
        >>> verifyObject(IGroup, teachers)
        True
        >>> students = app['groups']['students']
        >>> verifyObject(IGroup, students)
        True
        >>> courses = app['groups']['courses']
        >>> verifyObject(IGroup, courses)
        True

    """

def doctest_Course():
    r"""Tests for course groups.

        >>> from schooltool.app import Course
        >>> algebraI= Course("Algebra I", "First year math.")
        >>> from schooltool.interfaces import ICourse
        >>> verifyObject(ICourse, algebraI)
        True
        >>> from schoolbell.app.interfaces import IGroup
        >>> verifyObject(IGroup, algebraI)
        True

    """

def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schooltool.app',
                                     optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
