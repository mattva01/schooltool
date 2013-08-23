#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Unit tests for basic person security.
"""
import unittest
import doctest

from schooltool.relationship.tests import setUp, tearDown


def doctest_PersonAdvisorsCrowd():
    """Tests for PersonAdvisorsCrowd.

    We'll create an advisor and two students.

        >>> from schooltool.basicperson.person import BasicPerson
        >>> student1 = BasicPerson("student", "Student", "One")
        >>> student2 = BasicPerson("student", "Student", "Two")
        >>> advisor = BasicPerson("advisor", "Advisor", "One")

    The advisor will only advise the first student.

        >>> student1.advisors.add(advisor)

    Hence, the advisor will belong to the first student's advisors crowd and
    not the second.
    
        >>> from schooltool.basicperson.security import PersonAdvisorsCrowd
        >>> PersonAdvisorsCrowd(student1).contains(advisor)
        True
        >>> PersonAdvisorsCrowd(student2).contains(advisor)
        False

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return doctest.DocTestSuite(optionflags=optionflags,
                                setUp=setUp, tearDown=tearDown)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
