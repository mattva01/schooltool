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
Tests for schooltool term views.
"""
import unittest
import doctest
from datetime import date

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest

from schooltool.term.term import Term
from schooltool.term.ftesting import term_functional_layer
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.skin import ISchoolToolSkin
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.schoolyear.testing import provideStubAdapter
from schooltool.schoolyear.testing import provideStubUtility
from schooltool.schoolyear.testing import setUp
from schooltool.schoolyear.testing import tearDown
from schooltool.term.browser.term import TermEditForm
from schooltool.term.browser.term import TermAddForm


def doctest_TermAddForm():
    """Test for term add view.

    Let's add a school year

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                               date(2005, 9, 1),
        ...                               date(2006, 7, 16))

    Fill in the form

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.add' : u'Add',
        ...                 'form.widgets.title': u'Fall',
        ...                 'form.widgets.first': u'2005-09-01',
        ...                 'form.widgets.last' : u'2005-12-31'}

    And submit it

        >>> view = TermAddForm(sy, request)
        >>> view.update()
        >>> view.widgets.errors
        ()

    Now we can look at our newly added term

        >>> term = sy['fall']
        >>> term.title, term.first, term.last
        (u'Fall', datetime.date(2005, 9, 1), datetime.date(2005, 12, 31))

    """


def doctest_TermAddForm_overlap():
    """Test for term add view when the new term overlaps an old one.

     Let's add a school year

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                                    date(2005, 9, 1),
        ...                                    date(2006, 7, 16))

     And one term

        >>> sy['fall'] = Term("Fall",
        ...                   date(2005, 9, 1),
        ...                   date(2006, 7, 16))

     Fill in the form providing a date range that overlaps the term we
     just added

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.next' : u'Next',
        ...                 'form.widgets.title': u'Spring',
        ...                 'form.widgets.first': u'2005-09-01',
        ...                 'form.widgets.last' : u'2005-12-31'}

     And submit the form

        >>> view = TermAddForm(sy, request)
        >>> view.update()

     We should get an error message

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">
        Date range you have selected overlaps with the following term(s):
        <div> <a href="http://127.0.0.1/schoolyears/2005-2006/fall">Fall</a> (2005-09-01 &mdash; 2006-07-16) </div>
        </div>

     And only have the old term in the school year:

        >>> list(sy.keys())
        [u'fall']

    """


def doctest_TermAddForm_out_of_bounds():
    """Test for term add view when adding a term that does not fit in the school year.

    Let's add a school year

       >>> app = ISchoolToolApplication(None)
       >>> syc = ISchoolYearContainer(app)
       >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
       ...                                    date(2005, 9, 1),
       ...                                    date(2006, 7, 16))

    Fill in the form

       >>> request = TestRequest()
       >>> directlyProvides(request, [ISchoolToolSkin])
       >>> request.form = {'form.buttons.next' : u'Next',
       ...                 'form.widgets.title': u'Spring',
       ...                 'form.widgets.first': u'2005-08-01',
       ...                 'form.widgets.last' : u'2005-12-31'}

    And submit it

       >>> view = TermAddForm(sy, request)
       >>> view.update()

    We should get an error

       >>> for error in view.widgets.errors: print error.render()
       <div class="error">Date is not in the school year.</div>

    The error should be displayed on the widget as well

       >>> print view.widgets['first'].error.render()
       <div class="error">Date is not in the school year.</div>

    There should be no terms in the container

       >>> list(sy.keys())
       []

    """


def doctest_TermEditForm_overlap():
    """Test for term editing form when making one term overlapping another.

    Let's add a school year

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                                    date(2005, 9, 1),
        ...                                    date(2006, 7, 16))

    And a couple of terms

        >>> sy['fall'] = Term("Fall",
        ...                   date(2005, 9, 1),
        ...                   date(2006, 1, 1))

        >>> term = sy['spring'] = Term("Spring",
        ...                            date(2006, 1, 2),
        ...                            date(2006, 7, 16))

    Fill in the form

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.apply': u'Save changes',
        ...                 'form.widgets.title': u'Spring',
        ...                 'form.widgets.first': u'2006-01-01',
        ...                 'form.widgets.last' : u'2006-07-16'}
        >>> view = TermEditForm(term, request)
        >>> view.update()

    We should get an error

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">
        Date range you have selected overlaps with the following term(s):
        <div> <a href="http://127.0.0.1/schoolyears/2005-2006/fall">Fall</a> (2005-09-01 &mdash; 2006-01-01) </div>
        </div>

    The term should not get modified

        >>> term.first, term.last, term.title
        (datetime.date(2006, 1, 2), datetime.date(2006, 7, 16), 'Spring')

    """


def doctest_TermEditForm_overflow():
    """Test term editing form when making a term overflow a school year.

    Let's add a school year

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                                    date(2005, 9, 1),
        ...                                    date(2006, 7, 16))

    And a term

        >>> term = sy['spring'] = Term("Spring",
        ...                            date(2006, 1, 2),
        ...                            date(2006, 7, 16))

    Fill in the form

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.apply': u'Save changes',
        ...                 'form.widgets.title': u'Spring',
        ...                 'form.widgets.first': u'2006-01-02',
        ...                 'form.widgets.last' : u'2006-07-17'}

    And submit it

        >>> view = TermEditForm(term, request)
        >>> view.update()

    We should get an error

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">Date is not in the school year.</div>

    And term should stay the same

        >>> term.first, term.last, term.title
        (datetime.date(2006, 1, 2), datetime.date(2006, 7, 16), 'Spring')

    """


def doctest_TermEditForm_switch_dates():
    """Test term editing form when making a term with first date after the last one.

    Let's add a school year

        >>> app = ISchoolToolApplication(None)
        >>> syc = ISchoolYearContainer(app)
        >>> sy = syc['2005-2006'] = SchoolYear("2005-2006",
        ...                                    date(2005, 9, 1),
        ...                                    date(2006, 7, 16))

    And add a term

        >>> term = sy['spring'] = Term("Spring",
        ...                            date(2006, 1, 2),
        ...                            date(2006, 7, 16))

    Fill in the form switching start and end dates

        >>> request = TestRequest()
        >>> directlyProvides(request, [ISchoolToolSkin])
        >>> request.form = {'form.buttons.apply': u'Save changes',
        ...                 'form.widgets.title': u'Spring',
        ...                 'form.widgets.first': u'2006-07-10',
        ...                 'form.widgets.last' : u'2006-01-02'}

    And submit it

        >>> view = TermEditForm(term, request)
        >>> view.update()

    We should get an error

        >>> for error in view.widgets.errors: print error.render()
        <div class="error">Term must begin before it ends.</div>

    And term should stay the same

        >>> term.first, term.last, term.title
        (datetime.date(2006, 1, 2), datetime.date(2006, 7, 16), 'Spring')

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = term_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
