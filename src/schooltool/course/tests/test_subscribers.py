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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for course and section subscriber validation.
"""

import unittest
import doctest
from datetime import date, timedelta

from schooltool.schoolyear.testing import (setUp, tearDown,
                                           provideStubUtility,
                                           provideStubAdapter)
from schooltool.schoolyear.ftesting import schoolyear_functional_layer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.term.interfaces import ITerm
from schooltool.term.term import Term
from schooltool.course.interfaces import ISectionContainer
from schooltool.course.section import Section


def setUpSchoolYear(year=2000):
    year_container = ISchoolYearContainer(ISchoolToolApplication(None))
    sy = year_container[str(year)] = SchoolYear(
        str(year), date(year, 1, 1), date(year+1, 1, 1) - timedelta(1))
    return sy


def setUpTerms(schoolyear, term_count=3):
    term_delta = timedelta(
        ((schoolyear.last - schoolyear.first) / term_count).days)
    start_date = schoolyear.first
    for n in range(term_count):
        finish_date = start_date + term_delta - timedelta(1)
        schoolyear['Term%d' % (n+1)] = Term(
            'Term %d' % (n+1), start_date, finish_date)
        start_date = finish_date + timedelta(1)


def setUpSections(term_list, sections_per_term=1):
    for term in term_list:
        sections = ISectionContainer(term)
        for n in range(sections_per_term):
            name = 'Sec%d'%(n+1)
            sections[name] = Section(name)


def doctest_Section_linking_terms():
    r"""Tests for section linking term continuinity validations.

    Set up a school year with three terms, each containing two sections.

        >>> year = setUpSchoolYear(2000)
        >>> setUpTerms(year, 3)
        >>> setUpSections(year.values(), sections_per_term=2)

    Let's make Sec1 span the three terms.

        >>> s1_t1 = ISectionContainer(year['Term1'])['Sec1']
        >>> s1_t2 = ISectionContainer(year['Term2'])['Sec1']
        >>> s1_t3 = ISectionContainer(year['Term3'])['Sec1']

        >>> s1_t2.previous = s1_t1
        >>> s1_t2.next = s1_t3

        >>> for s in s1_t2.linked_sections:
        ...     print '%s, %s' % (ITerm(s).title, s.title)
        Term 1, Sec1
        Term 2, Sec1
        Term 3, Sec1

    We cannot link a section to another section in the same term.

        >>> s2_t1 = ISectionContainer(year['Term1'])['Sec2']
        >>> s2_t2 = ISectionContainer(year['Term2'])['Sec2']
        >>> s2_t3 = ISectionContainer(year['Term3'])['Sec2']

        >>> s2_t2.next = s1_t2
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException: Cannot link sections in same term

        >>> s2_t2.previous = s1_t2
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException: Cannot link sections in same term

    Cannot set previous section in the future.

        >>> s2_t2.previous = s1_t3
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException:
        Sections must be in consecutive terms

    Or set next section in the past.

        >>> s2_t2.next = s1_t1
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException:
        Sections must be in consecutive terms

    Notice that though we tried to link Sec2 with Sec1, we didn't change it's
    linked_sections, becouse all our assigments were invalid.

        >>> for s in s1_t2.linked_sections:
        ...     print '%s, %s' % (ITerm(s).title, s.title)
        Term 1, Sec1
        Term 2, Sec1
        Term 3, Sec1

    Sections can be linked only in terms next to each other.  Try to link
    section in term 3 with section in term 1.

        >>> s2_t3.previous = s1_t1
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException:
        Sections must be in consecutive terms

    Linking failed, so nothing changed in linked_sections.

        >>> for s in s1_t2.linked_sections:
        ...     print '%s, %s' % (ITerm(s).title, s.title)
        Term 1, Sec1
        Term 2, Sec1
        Term 3, Sec1

    """


def doctest_Section_linking_schoolyears():
    r"""Tests for section linking SchoolYear validations.

    Set up a school year with three terms, each containing two sections.

        >>> def setUpYearWithSection(year):
        ...     year = setUpSchoolYear(year)
        ...     setUpTerms(year, 1)
        ...     setUpSections(year.values(), sections_per_term=1)
        ...     return year

        >>> year0 = setUpYearWithSection(2000)
        >>> year1 = setUpYearWithSection(2001)
        >>> year2 = setUpYearWithSection(2002)

        >>> sec_year_0 = ISectionContainer(year0['Term1'])['Sec1']
        >>> sec_year_1 = ISectionContainer(year1['Term1'])['Sec1']
        >>> sec_year_2 = ISectionContainer(year2['Term1'])['Sec1']

    We cannot link sections in the different school years.

        >>> sec_year_1.previous = sec_year_0
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException:
        Cannot link sections in different school years

        >>> sec_year_1.next = sec_year_2
        Traceback (most recent call last):
        ...
        InvalidSectionLinkException:
        Cannot link sections in different school years

    """


def doctest_copySection():
    r"""Test for copySection.

        >>> from schooltool.course.course import Course
        >>> from schooltool.person.person import Person

    Create a section with a course, instructor and several members.

        >>> year = setUpSchoolYear(2000)
        >>> setUpTerms(year, 2)

        >>> section = Section('English A')
        >>> section.instructors.add(Person('teacher', 'Mr. Jones'))
        >>> section.members.add(Person('first','First'))
        >>> section.members.add(Person('second','Second'))
        >>> section.members.add(Person('third','Third'))
        >>> section.courses.add(Course(title="English"))
        >>> ISectionContainer(year['Term1'])['Sec1'] = section

    Let's copy it to another term.

        >>> from schooltool.course.section import copySection

        >>> new_section = copySection(section, year['Term2'])

    Sectoin's copy was created.

        >>> new_section is not section
        True

    Sec1 was available as section id in the new term, so it was preserved.

        >>> print new_section.__name__
        Sec1

    Courses, instructors and members were copied.

        >>> for course in new_section.courses:
        ...     print course.title
        English

        >>> for person in new_section.instructors:
        ...     print person.title
        Mr. Jones

        >>> for person in new_section.members:
        ...     print person.title
        First
        Second
        Third

    If original section's __name__ is already present in the target term, an
    alternative is chosen.

        >>> other_section = copySection(section, year['Term2'])
        >>> print other_section.__name__
        1

    """


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
