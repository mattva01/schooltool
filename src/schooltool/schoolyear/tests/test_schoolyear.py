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
"""
Tests for school years
"""
import unittest
import doctest
from datetime import date

from zope.interface.verify import verifyObject

from schooltool.term.term import Term
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.testing import (setUp, tearDown,
                                           provideStubUtility,
                                           provideStubAdapter)
from schooltool.schoolyear.ftesting import schoolyear_functional_layer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.schoolyear.schoolyear import SCHOOLYEAR_CONTAINER_KEY


def doctest_SchoolYearContainer():
    """Test for SchoolYear container

    When application starts up, the top level container should be there:

       >>> app = ISchoolToolApplication(None)
       >>> schoolyear_container = app[SCHOOLYEAR_CONTAINER_KEY]
       >>> schoolyear_container
       <schooltool.schoolyear.schoolyear.SchoolYearContainer object at ...>

       >>> verifyObject(ISchoolYearContainer, schoolyear_container)
       True

    __parent__ should be set properly:

       >>> schoolyear_container.__parent__ is app
       True

    We can access the container by adapting the application to
    ISchoolYearContainer:

       >>> ISchoolYearContainer(app) is schoolyear_container
       True

    """


def doctest_SchoolYearContainer_schoolyear_activation():
    """Test for school year activation in school year container

       >>> app = ISchoolToolApplication(None)
       >>> syc = ISchoolYearContainer(app)

    When we have no school years both active school year and next
    school year should return None:

       >>> syc.getActiveSchoolYear() is None
       True

       >>> syc.getNextSchoolYear() is None
       True

    active_id should be None as well

       >>> syc.active_id is None
       True

    but if we add a school year (it does not matter when it starts)

        >>> sy1 = SchoolYear("2005-2006", date(2005, 9, 1), date(2006, 7, 15))
        >>> syc['2005-2006'] = sy1

    it automatically becomes active

        >>> syc.getActiveSchoolYear() is sy1
        True
        >>> syc.active_id
        '2005-2006'

    though - next school year is still None

        >>> syc.getNextSchoolYear() is None
        True

    if we will add another school year, one before the active one, it
    will not get marked as the next school year

        >>> sy0 = SchoolYear("2004-2005", date(2004, 9, 1), date(2005, 7, 15))
        >>> syc['2004-2005'] = sy0

        >>> syc.getNextSchoolYear() is None
        True

    next schol year must come *after* the active one

        >>> sy2 = SchoolYear("2006-2007", date(2006, 9, 1), date(2007, 7, 15))
        >>> syc['2006-2007'] = sy2

        >>> syc.getNextSchoolYear() is sy2
        True

    we can't modify the active_id by hand

        >>> syc.active_id = '2004-2005'
        Traceback (most recent call last):
        ...
        AttributeError: can't set attribute

    we must use the activateNextSchoolYear function that automatically
    activates the next school year

        >>> syc.activateNextSchoolYear()
        >>> syc.getActiveSchoolYear() is sy2
        True
        >>> syc.getNextSchoolYear() is None
        True

    You can pass a schoolyear key to override the "default" next.

        >>> syc.activateNextSchoolYear(year_id=sy1.__name__)
        >>> syc.getActiveSchoolYear() is sy1
        True
        >>> syc.getNextSchoolYear() is sy2
        True

    """


def doctest_SchoolYear():
    """Test for SchoolYear

    School years are term like objects, that are kept in the
    schoolyear container. To construct one you must pass a title and 2
    dates to it's constructor:

        >>> sy = SchoolYear("2005-2006", date(2005, 9, 1), date(2006, 7, 15))

    Title, first and last date of the school year get set:

        >>> sy.title, sy.first, sy.last
        ('2005-2006', datetime.date(2005, 9, 1), datetime.date(2006, 7, 15))

    All school years implement ISchoolYear interface:

        >>> verifyObject(ISchoolYear, sy)
        True

    School years are kept in the schoolyear container:

        >>> syc = ISchoolYearContainer(ISchoolToolApplication(None))
        >>> syc['2005-2006'] = sy

    """


def doctest_SchoolYear_first_before_last():
    """Tests for SchoolYear

    The first day of a schoolyear must come before the last day.

        >>> sy = SchoolYear("2005-2006", date(2005, 9, 1), date(2005, 7, 15))
        Traceback (most recent call last):
        ...
        ValueError: Last date datetime.date(2005, 7, 15) less than
        first date datetime.date(2005, 9, 1)

   We cannot trick that constraint by sneakily trying to change the
   attributes after creation

        >>> sy = SchoolYear("2005-2006", date(2005, 9, 1), date(2006, 7, 15))
        >>> sy.first = date(2006, 9, 1)
        Traceback (most recent call last):
        ...
        ValueError: Last date datetime.date(2006, 7, 15) less than
        first date datetime.date(2006, 9, 1)

        >>> sy.first
        datetime.date(2005, 9, 1)

        >>> sy.last = date(2005, 7, 1)
        Traceback (most recent call last):
        ...
        ValueError: Last date datetime.date(2005, 7, 1) less than
        first date datetime.date(2005, 9, 1)

        >>> sy.last
        datetime.date(2006, 7, 15)

    One-day schoolyears are valid, albeit silly

        >>> sy = SchoolYear("2005-2006", date(2005, 9, 1), date(2005, 9, 1))

    We should still be able to set the same dates through first and last:

        >>> sy.first = date(2005, 9, 1)

        >>> sy.last = date(2005, 9, 1)

    Expanding the school year should work as well:

        >>> sy.first = date(2004, 9, 1)

        >>> sy.last = date(2006, 9, 1)

    """


def doctest_SchoolYearContainer_years_must_not_overlap():
    """Test for SchoolYearContainer and SchoolYear interaction

    School years container is for keeping school years:

        >>> syc = ISchoolYearContainer(ISchoolToolApplication(None))
        >>> sy1 = SchoolYear("2005-2006", date(2005, 9, 1), date(2006, 7, 15))
        >>> syc['2005-2006'] = sy1

        >>> sy2 = SchoolYear("2006-2007", date(2006, 9, 1), date(2007, 7, 15))
        >>> syc['2006-2007'] = sy2

    Even though you can create a schoolyear that overlaps other
    schoolyears:

        >>> sy3 = SchoolYear("2005-2007", date(2005, 9, 1), date(2007, 1, 12))

    You can't add it to the SchoolYearContainer :

        >>> syc['2005-2007'] = sy3
        Traceback (most recent call last):
        ...
        SchoolYearOverlapError: SchoolYear '2005-2007' overlaps with
          SchoolYear(s) (2005-2006, 2006-2007)

    You can't work around the restriction by changing schoolyears that
    are already in the container either:

        >>> sy1.last = date(2007, 1, 12)
        Traceback (most recent call last):
        ...
        SchoolYearOverlapError: SchoolYear '2005-2006' overlaps
        with SchoolYear(s) (2006-2007)

        >>> sy1.last
        datetime.date(2006, 7, 15)

        >>> sy2.first = date(2005, 9, 1)
        Traceback (most recent call last):
        ...
        SchoolYearOverlapError: SchoolYear '2006-2007' overlaps
        with SchoolYear(s) (2005-2006)

        >>> sy2.first
        datetime.date(2006, 9, 1)

    """


def doctest_SchoolYear_terms_must_not_overlap():
    """Test for school years with terms in them

    School years can have terms in them:

        >>> syc = ISchoolYearContainer(ISchoolToolApplication(None))
        >>> sy = SchoolYear("2005-2006", date(2005, 9, 1), date(2006, 7, 15))
        >>> syc['2005-2006'] = sy

        >>> fall = sy['fall'] = Term("Fall", date(2005, 9, 1), date(2006, 1, 12))
        >>> spring = sy['spring'] = Term("Spring", date(2006, 1, 13), date(2006, 7, 15))

    Terms can't overlap:

        >>> syc['2005-2006']['fall_2'] = Term("Fall 2", date(2005, 9, 1), date(2006, 1, 12))
        Traceback (most recent call last):
        ...
        TermOverlapError: Date range you have selected overlaps with term(s) (Fall)

    You can't work around the restriction by changing terms
    directly either:

        >>> fall.last = date(2006, 1, 17)
        Traceback (most recent call last):
        ...
        TermOverlapError: Date range you have selected overlaps with term(s) (Spring)

        >>> fall.last
        datetime.date(2006, 1, 12)

        >>> spring.first = date(2005, 10, 15)
        Traceback (most recent call last):
        ...
        TermOverlapError: Date range you have selected overlaps with term(s) (Fall)

        >>> spring.first
        datetime.date(2006, 1, 13)

    """


def doctest_SchoolYear_terms_must_be_fully_contained():
    """Test for Term and SchoolYear interaction

    School years can have terms in them:

        >>> syc = ISchoolYearContainer(ISchoolToolApplication(None))
        >>> sy = SchoolYear("2005-2006", date(2005, 9, 1), date(2006, 7, 15))
        >>> syc['2005-2006'] = sy

        >>> sy['fall'] = Term("Fall", date(2005, 9, 1), date(2006, 1, 12))
        >>> sy['spring'] = Term("Spring", date(2006, 1, 13), date(2006, 7, 15))

    But term dates are limited to the ones that are in the range of
    the school year:

        >>> sy['fall'] = Term("Fall", date(2006, 8, 31), date(2007, 1, 12))
        Traceback (most recent call last):
        ...
        ValueError: Term can't end after the school year ends!

        >>> sy['fall'] = Term("Fall", date(2006, 9, 1), date(2007, 7, 16))
        Traceback (most recent call last):
        ...
        ValueError: Term can't end after the school year ends!

    You can't work around these limmitations by modifying the term
    after it was added:

        >>> sy['fall'].first = date(2005, 8, 1)
        Traceback (most recent call last):
        ...
        TermDateNotInSchoolYear: ...

    Also you should be unable to shrink the school year without
    changing boundaries of the terms first:

        >>> sy.first = date(2005, 9, 2)
        Traceback (most recent call last):
        ...
        TermOverflowError: Date range you are trying to set is too small to
        contain following term(s) (Fall)

        >>> sy.last = date(2006, 6, 15)
        Traceback (most recent call last):
        ...
        TermOverflowError: Date range you are trying to set is too small to
        contain following term(s) (Spring)

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
