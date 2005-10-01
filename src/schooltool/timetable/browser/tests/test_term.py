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
Tests for schooltool term views.

$Id: test_timetable.py 4822 2005-08-19 01:35:11Z srichter $
"""
import datetime
import unittest

from zope.i18n import translate
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.traversing.interfaces import IContainmentRoot

from schooltool.app.browser import testing
from schooltool.timetable.browser.tests.test_timetable import setUp, tearDown
from schooltool.timetable.browser.tests.test_timetable import print_cal


def doctest_TermView_calendar():
    '''Unit tests for TermAddView.calendar

        >>> from schooltool.timetable.term import Term
        >>> from schooltool.timetable.browser.term import TermView
        >>> context = Term('Sample', datetime.date(2004, 8, 1),
        ...                        datetime.date(2004, 8, 31))
        >>> request = TestRequest()
        >>> view = TermView(context, request)

    This view has just one method, `calendar`, that invokes TermRenderer
    to give a nice structure of lists and dicts for the page template.

        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31

    '''


def doctest_TermEditView_title():
    '''Unit tests for TermEditView.title

        >>> from schooltool.timetable.term import Term
        >>> from schooltool.timetable.browser.term import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 1),
        ...                        datetime.date(2004, 8, 31))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    view.title returns a Zope 3 I18N Message ID.

        >>> view.title()
        u'Change Term: $title'
        >>> translate(view.title())
        u'Change Term: Sample'

    '''


def doctest_TermEditView_calendar():
    '''Unit tests for TermEditView.calendar

        >>> from schooltool.timetable.term import Term
        >>> from schooltool.timetable.browser.term import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 4),
        ...                        datetime.date(2004, 8, 6))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    view.calendar() always renders view.term

        >>> view.term = Term('Sample', datetime.date(2004, 8, 1),
        ...                          datetime.date(2004, 8, 12))
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12

    '''


def doctest_TermEditView_update():
    '''Unit tests for TermEditView.update

        >>> from schooltool.timetable.term import Term
        >>> from schooltool.timetable.browser.term import TermEditView
        >>> context = Term('Sample', datetime.date(2004, 8, 4),
        ...                        datetime.date(2004, 8, 6))
        >>> request = TestRequest()
        >>> view = TermEditView(context, request)

    When there are no dates in the request, or when the dates are not valid,
    view.update() sets self.term to self.context (so that the unchanged
    term calendar is then rendered by view.calendar()).  It also sets
    update_status.

        >>> view.update()
        ''
        >>> view.update_status
        ''
        >>> view.term is view.context
        True

    If you call view.update again, it will notice that update_status is
    set and do nothing.

        >>> request.form['field.title'] = 'Sample'
        >>> request.form['field.first'] = '2005-08-01'
        >>> request.form['field.last'] = '2005-08-05'
        >>> view.update()
        ''
        >>> view.term is view.context
        True

    However if you reset update_status back to None, update will 

        >>> view.update_status = None
        >>> view.update()
        ''
        >>> view.term is view.context
        False
        >>> view.term.first
        datetime.date(2005, 8, 1)
        >>> view.term.last
        datetime.date(2005, 8, 5)

    If UPDATE_SUBMIT appears in the request, update changes view.context
    and sends an ObjectModifiedEvent.

        >>> import zope.event
        >>> from zope.app.event.interfaces import IObjectModifiedEvent
        >>> old_subscribers = zope.event.subscribers[:]
        >>> def modified_handler(event):
        ...     if IObjectModifiedEvent.providedBy(event):
        ...         print "*** Object modified ***"
        >>> zope.event.subscribers.append(modified_handler)

        >>> request.form['UPDATE_SUBMIT'] = 'Save'
        >>> request.form['holiday'] = '2005-08-03'
        >>> view.update_status = None
        >>> view.update()
        *** Object modified ***
        u'Saved changes.'
        >>> context.first
        datetime.date(2005, 8, 1)
        >>> context.last
        datetime.date(2005, 8, 5)
        >>> context.isSchoolday(datetime.date(2005, 8, 2))
        True
        >>> context.isSchoolday(datetime.date(2005, 8, 3))
        False

        >>> zope.event.subscribers[:] = old_subscribers

    '''


def doctest_TermAddView_update():
    '''Unit tests for TermAddView.update

    `update` sets view.term

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)
        >>> view.update()
        >>> view.term is None
        True

        >>> request.form['field.title'] = 'Sample'
        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = '2005-10-15'
        >>> view.update()
        >>> view.term
        <...Term object at ...>

    '''


def doctest_TermAddView_create():
    '''Unit tests for TermAddView.create

    `create` either returns view.term (if it has been successfully built
    by `update` before), or raises a WidgetsError (because `_buildTerm`
    discovered an error in the form).

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> view.term = object()
        >>> view.create() is view.term
        True

        >>> view.term = None
        >>> view.create()
        Traceback (most recent call last):
          ...
        WidgetsError

    '''


def doctest_TermAddView_add():
    r'''Unit tests for TermAddView.add

    `add` adds the term to the term service.

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.term import Term
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> term = Term('Sample', datetime.date(2005, 1, 1),
        ...                     datetime.date(2005, 12, 31))
        >>> view.add(term)

    The standard NameChooser adapter picks the name 'Term'.

        >>> print '\n'.join(context.keys())
        Term

        >>> context['Term'] is term
        True

    '''


def doctest_TermAddView_create():
    '''Unit tests for TermAddView.create

    `create` either returns view.term (if it has been successfully built
    by `update` before), or raises a WidgetsError (because `_buildTerm`
    discovered an error in the form).

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> view.term = object()
        >>> view.create() is view.term
        True

        >>> view.term = None
        >>> view.create()
        Traceback (most recent call last):
          ...
        WidgetsError

    '''


def doctest_TermAddView_nextURL():
    '''Unit tests for TermAddView.nextURL

    `nextURL` returns the absolute url of its context.

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> directlyProvides(context, IContainmentRoot)
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)
        >>> view.nextURL()
        'http://127.0.0.1'

    '''


def doctest_TermEditViewMixin_buildTerm():
    '''Unit tests for TermEditViewMixin._buildTerm

    We shall use TermAddView here -- it inherits TermEditViewMixin._buildTerm
    without changing it.

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

        >>> request.form['field.title'] = 'Sample'

    When there are no dates in the request, or when the dates are not valid,
    view._buildTerm() returns None.

        >>> view._buildTerm()

        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = 'not a clue'
        >>> view._buildTerm()

        >>> request.form['field.first'] = 'bogus'
        >>> request.form['field.last'] = '2005-12-31'
        >>> view._buildTerm()

        >>> request.form['field.first'] = '2005-12-31'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view._buildTerm()

    If the dates are valid, but the interval is not, you get None again.

        >>> request.form['field.first'] = '2005-09-02'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view._buildTerm()

    When the dates describe a valid non-empty inclusive time interval,
    view._buildTerm() returns a Term object.

        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = '2005-10-15'
        >>> term = view._buildTerm()
        >>> term.first
        datetime.date(2005, 9, 1)
        >>> term.last
        datetime.date(2005, 10, 15)
        >>> term.title
        u'Sample'

    When there are no indication about schooldays or holidays in the request,
    all days are marked as schooldays.

        >>> def print_holidays(term):
        ...     all = True
        ...     for day in term:
        ...         if not term.isSchoolday(day):
        ...             print "%s is a holiday" % day
        ...             all = False
        ...     if all:
        ...         print "All days are schooldays."

        >>> print_holidays(term)
        All days are schooldays.

        >>> request.form['holiday'] = u'2005-09-07'
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-07 is a holiday

        >>> request.form['holiday'] = [u'2005-10-02', u'2005-09-07']
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-07 is a holiday
        2005-10-02 is a holiday

    Ill-formed or out-of-range dates are just ignored

        >>> request.form['holiday'] = [u'2005-10-17', u'2005-09-07', u'foo!']
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-07 is a holiday

    The presence of 'TOGGLE_n' (where n is 0..6) in the request requests the
    state of corresponding weekdays (0 = Monday, 6 = Sunday) to be toggled.

        >>> request.form['holiday'] = [u'2005-10-02', u'2005-09-07']
        >>> request.form['TOGGLE_0'] = [u'Monday']
        >>> request.form['TOGGLE_6'] = [u'Sunday']
        >>> term = view._buildTerm()
        >>> print_holidays(term)
        2005-09-04 is a holiday
        2005-09-05 is a holiday
        2005-09-07 is a holiday
        2005-09-11 is a holiday
        2005-09-12 is a holiday
        2005-09-18 is a holiday
        2005-09-19 is a holiday
        2005-09-25 is a holiday
        2005-09-26 is a holiday
        2005-10-03 is a holiday
        2005-10-09 is a holiday
        2005-10-10 is a holiday

    '''


def doctest_TermAddView_calendar():
    '''Unit tests for TermAddView.calendar

        >>> from schooltool.timetable.term import TermContainer
        >>> from schooltool.timetable.browser.term import TermAddView
        >>> context = TermContainer()
        >>> request = TestRequest()
        >>> view = TermAddView(context, request)

    When there are no dates in the request, or when the dates are not valid,
    view.caledar() returns None

        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = '2005-09-01'
        >>> request.form['field.last'] = 'not a clue'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = 'bogus'
        >>> request.form['field.last'] = '2005-12-31'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = '2005-12-31'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

        >>> request.form['field.first'] = '2005-09-02'
        >>> request.form['field.last'] = '2005-09-01'
        >>> view.term = view._buildTerm()
        >>> view.calendar()

    When the dates describe a valid non-empty inclusive time interval,
    view.calendar() returns a list of dicts, one for each month.

        >>> request.form['field.title'] = 'Sample'
        >>> request.form['field.first'] = '2004-08-01'
        >>> request.form['field.last'] = '2004-08-31'
        >>> view.term = view._buildTerm()
        >>> print_cal(view.calendar())
        *                        August 2004
                 Mon Tue Wed Thu Fri Sat Sun
        Week 31:                           1
        Week 32:   2   3   4   5   6   7   8
        Week 33:   9  10  11  12  13  14  15
        Week 34:  16  17  18  19  20  21  22
        Week 35:  23  24  25  26  27  28  29
        Week 36:  30  31

    '''


def test_suite():
    suite = unittest.TestSuite()
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.REPORT_ONLY_FIRST_FAILURE |
                   doctest.NORMALIZE_WHITESPACE)
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    suite.addTest(doctest.DocFileSuite(
        'termrenderer.txt', setUp=setUp, tearDown=tearDown,
        globs={'print_cal': print_cal},
        optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
