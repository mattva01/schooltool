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
Tests for SchoolTool-specific calendar views.

$Id$
"""

import unittest
from datetime import date, timedelta, time
from zope.testing import doctest
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.app.tests import setup, ztapi
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass

from schoolbell.app.browser.tests.setup import setUp, tearDown

import schooltool.app
from schooltool import timetable
from schooltool.common import parse_datetime
from schooltool.interfaces import ApplicationInitializationEvent
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod
from schooltool.timetable import SequentialDaysTimetableModel
from pytz import timezone

utc = timezone('UTC')


def setUpSchoolToolSite():
    from schooltool.app import SchoolToolApplication
    app = SchoolToolApplication()

    # Usually automatically called subscribers
    schooltool.app.addCourseContainerToApplication(
        ApplicationInitializationEvent(app))
    schooltool.app.addSectionContainerToApplication(
        ApplicationInitializationEvent(app))
    timetable.addToApplication(ApplicationInitializationEvent(app))

    directlyProvides(app, IContainmentRoot)
    from zope.app.component.site import LocalSiteManager
    app.setSiteManager(LocalSiteManager(app))
    from zope.app.component.hooks import setSite
    setSite(app)
    return app


def dt(timestr):
    dt = parse_datetime('2004-11-05 %s:00' % timestr)
    return dt.replace(tzinfo=utc)


class TestDailyCalendarRowsView(unittest.TestCase):

    def setUp(self):
        from schooltool.app import getPersonPreferences
        from schooltool.interfaces import IPersonPreferences
        from schoolbell.app.interfaces import IHavePreferences

        # set up adaptation (the view checks user preferences)
        setup.placelessSetUp()
        setup.setUpAnnotations()
        ztapi.provideAdapter(IHavePreferences, IPersonPreferences,
                             getPersonPreferences)

        # set up the site
        app = setUpSchoolToolSite()
        from schooltool.app import Person
        self.person = app['persons']['person'] = Person('person')

        # set up the timetable schema
        days = ['A', 'B', 'C']
        schema = self.createSchema(days,
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'],
                                   ['1', '2', '3', '4'])
        template = SchooldayTemplate()
        template.add(SchooldayPeriod('1', time(8, 0), timedelta(hours=1)))
        template.add(SchooldayPeriod('2', time(10, 15), timedelta(hours=1)))
        template.add(SchooldayPeriod('3', time(11, 30), timedelta(hours=1)))
        template.add(SchooldayPeriod('4', time(12, 30), timedelta(hours=2)))
        schema.model = SequentialDaysTimetableModel(days, {None: template})

        app['ttschemas']['default'] = schema

        # set up terms
        from schooltool.timetable import Term
        app['terms']['term'] = term = Term("Some term", date(2004, 9, 1),
                                           date(2004, 12, 31))
        term.add(date(2004, 11, 5))

    def tearDown(self):
        setup.placelessTearDown()

    def createSchema(self, days, *periods_for_each_day):
        """Create a timetable schema."""
        from schooltool.timetable import TimetableSchema
        from schooltool.timetable import TimetableSchemaDay
        schema = TimetableSchema(days, title="A Schema")
        for day, periods in zip(days, periods_for_each_day):
            schema[day] = TimetableSchemaDay(list(periods))
        return schema

    def test_calendarRows(self):
        from schooltool.browser.cal import DailyCalendarRowsView
        from schoolbell.app.security import Principal

        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyCalendarRowsView(self.person.calendar, request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19))

        expected = [("1", dt('08:00'), timedelta(hours=1)),
                    ("9:00", dt('09:00'), timedelta(hours=1)),
                    ("10:00", dt('10:00'), timedelta(minutes=15)),
                    ("2", dt('10:15'), timedelta(hours=1)),
                    ("11:15", dt('11:15'), timedelta(minutes=15)),
                    ("3", dt('11:30'), timedelta(hours=1)),
                    ("4", dt('12:30'), timedelta(hours=2)),
                    ("14:30", dt('14:30'), timedelta(minutes=30)),
                    ("15:00", dt('15:00'), timedelta(hours=1)),
                    ("16:00", dt('16:00'), timedelta(hours=1)),
                    ("17:00", dt('17:00'), timedelta(hours=1)),
                    ("18:00", dt('18:00'), timedelta(hours=1))]

        self.assertEquals(result, expected)

    def test_calendarRows_no_periods(self):
        from schooltool.browser.cal import DailyCalendarRowsView
        from schooltool.app import getPersonPreferences
        from schoolbell.app.security import Principal

        prefs = getPersonPreferences(self.person)
        prefs.cal_periods = False # do not show periods
        request = TestRequest()
        principal = Principal('person', 'Some person', person=self.person)
        request.setPrincipal(principal)
        view = DailyCalendarRowsView(self.person.calendar, request)

        result = list(view.calendarRows(date(2004, 11, 5), 8, 19))

        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)

    def test_calendarRows_default(self):
        from schooltool.browser.cal import DailyCalendarRowsView

        request = TestRequest()
        # do not set the principal
        view = DailyCalendarRowsView(self.person.calendar, request)
        result = list(view.calendarRows(date(2004, 11, 5), 8, 19))

        # the default is not to show periods
        expected = [("%d:00" % i, dt('%d:00' % i), timedelta(hours=1))
                    for i in range(8, 19)]
        self.assertEquals(result, expected)


def doctest_CalendarSTOverlayView():
    r"""Tests for CalendarSTOverlayView

        >>> from schooltool.browser.cal import CalendarSTOverlayView
        >>> View = SimpleViewClass('../templates/calendar_overlay.pt',
        ...                        bases=(CalendarSTOverlayView,))

    CalendarOverlayView is a view on anything.

        >>> context = object()
        >>> request = TestRequest()
        >>> view = View(context, request)

    It renders to an empty string unless its context is the calendar of the
    authenticated user

        >>> view()
        u'\n'

    If you are an authenticated user looking at your own calendar, this view
    renders a calendar selection portlet.

        >>> from schooltool.app import Person, Group, Section, Course
        >>> from schoolbell.app.security import Principal
        >>> app = setUpSchoolToolSite()
        >>> person = app['persons']['whatever'] = Person('fred')
        >>> group1 = app['groups']['g1'] = Group(title="Group 1")
        >>> group2 = app['groups']['g2'] = Group(title="Group 2")
        >>> history = app['courses']['c1'] = Course(title="History")
        >>> section = app['sections']['s1'] = Section()
        >>> history.sections.add(section)
        >>> person.overlaid_calendars.add(group1.calendar, show=True,
        ...                               show_timetables=False)
        >>> person.overlaid_calendars.add(group2.calendar, show=False,
        ...                               show_timetables=True)
        >>> person.overlaid_calendars.add(section.calendar, show=False,
        ...                               show_timetables=True)
        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> view = View(person.calendar, request)

        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        ...<input type="checkbox" checked="checked" disabled="disabled" />...
        ...<input type="checkbox" name="my_timetable"
                  checked="checked" />...
        ...My Calendar...
        ...
        ...<input type="checkbox" name="overlay:list"
                  checked="checked" value="/groups/g1" />...
        ...<input type="checkbox"
                  name="overlay_timetables:list"
                  value="/groups/g1" />...
        ...
        ...<input type="checkbox" name="overlay:list"
                  value="/groups/g2" />...
        ...<input type="checkbox" name="overlay_timetables:list"
                  checked="checked" value="/groups/g2" />...
        ...<td style="width: 100%">Group 2</td>...
        ...
        ...<input type="checkbox" name="overlay:list"
                  value="/sections/s1" />...
        ...<input type="checkbox" name="overlay_timetables:list"
                  checked="checked" value="/sections/s1" />...
        ...<td style="width: 100%"> -- History</td>...
        ...
        </div>

    If the request has 'OVERLAY_APPLY', CalendarOverlayView applies your
    changes

        >>> request.form['overlay'] = [u'/groups/g2']
        >>> request.form['overlay_timetables'] = [u'/groups/g1']
        >>> request.form['OVERLAY_APPLY'] = u"Apply"
        >>> print view()
        <div id="portlet-calendar-overlay" class="portlet">
        ...
        ...<input type="checkbox" checked="checked" disabled="disabled" />...
        ...<input type="checkbox" name="my_timetable" />...
        ...My Calendar...
        ...
        ...<input type="checkbox" name="overlay:list"
                  value="/groups/g1" />...
        ...<input type="checkbox"
                  name="overlay_timetables:list"
                  checked="checked" value="/groups/g1" />...
        ...
        ...<input type="checkbox" name="overlay:list"
                  checked="checked" value="/groups/g2" />...
        ...<input type="checkbox" name="overlay_timetables:list"
                  value="/groups/g2" />...
        ...
        </div>

    It also redirects you to request.URL:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    There are two reasons for the redirect: first, part of the page template
    just rendered might have become invalid when calendar overlay selection
    changed, second, this lets the user refresh the page without having to
    experience confirmation dialogs that say "Do you want to POST this form
    again?".

    If the request has 'OVERLAY_MORE', CalendarOverlayView redirects to
    calendar_selection.html

        >>> request = TestRequest()
        >>> request.setPrincipal(Principal('id', 'title', person))
        >>> request.form['OVERLAY_MORE'] = u"More..."
        >>> view = View(person.calendar, request)
        >>> content = view()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1/persons/fred/calendar_selection.html?nexturl=http%3A//127.0.0.1'

    """


def doctest_CalendarListView(self):
    """Tests for CalendarListView.

    This view only has the getCalendars() method.

    The difference between this view and the one in SchoolBell is that this
    view knows about timetables and may return timetable calendars as well.
    The color of each timetable calendar is the same as of the corresponding
    personal calendar.

    CalendarListView.getCalendars returns a list of calendars that
    should be displayed.  This list always includes the context of
    the view, but it may also include other calendars as well.

    A handful of useful stubs:

        >>> class CalendarStub:
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def _getParent(self):
        ...         return PersonStub(self.title, self)
        ...     __parent__ = property(_getParent)

        >>> class OverlayInfoStub:
        ...     def __init__(self, title, color1, color2,
        ...                  show=True, show_timetables=True):
        ...         self.calendar = CalendarStub(title)
        ...         self.color1 = color1
        ...         self.color2 = color2
        ...         self.show = show
        ...         self.show_timetables = show_timetables

        >>> from schoolbell.app.interfaces import IPersonPreferences
        >>> from zope.interface import implements
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> from schooltool.timetable.interfaces import ITimetabled
        >>> class PersonStub:
        ...     implements(IAttributeAnnotatable, ITimetabled)
        ...     def __init__(self, title, calendar=None):
        ...         self.title = title
        ...         self.calendar = calendar
        ...     def makeTimetableCalendar(self):
        ...         return CalendarStub(self.title + ' (timetable)')
        ...     def __conform__(self, interface):
        ...         if interface is IPersonPreferences:
        ...             return PreferenceStub()
        ...     overlaid_calendars = [
        ...         OverlayInfoStub('Other Calendar', 'red', 'blue',
        ...                         True, False),
        ...         OverlayInfoStub('Another Calendar', 'green', 'red',
        ...                         False, True),
        ...         OverlayInfoStub('Interesting Calendar', 'yellow', 'white',
        ...                         True, True),
        ...         OverlayInfoStub('Boring Calendar', 'brown', 'magenta',
        ...                         False, False)]

        >>> class PreferenceStub:
        ...     def __init__(self):
        ...         self.weekstart = pycalendar.MONDAY
        ...         self.timeformat = "%H:%M"
        ...         self.dateformat = "YYYY-MM-DD"
        ...         self.timezone = 'UTC'

    A simple check:

        >>> from schooltool.browser.cal import CalendarListView
        >>> import calendar as pycalendar
        >>> calendar = CalendarStub('My Calendar') 
        >>> request = TestRequest()
        >>> view = CalendarListView(calendar, request)
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        My Calendar (timetable) (#9db8d2, #7590ae)

    If the authenticated user is looking at his own calendar, then
    a list of overlaid calendars is taken into consideration

        >>> from schoolbell.app.interfaces import IPerson
        >>> class PrincipalStub:
        ...     def __init__(self):
        ...         self.person = PersonStub('x', calendar=calendar)
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return self.person
        >>> principal = PrincipalStub()
        >>> request.setPrincipal(principal)

        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        My Calendar (timetable) (#9db8d2, #7590ae)
        Other Calendar (red, blue)
        Another Calendar (timetable) (green, red)
        Interesting Calendar (yellow, white)
        Interesting Calendar (timetable) (yellow, white)

    If the person has the current timetable display unchecked, the composite
    timetable calendar is not included in the list:

        >>> from zope.app.annotation.interfaces import IAnnotations
        >>> annotations = IAnnotations(principal.person)
        >>> from schooltool.browser.cal import CalendarSTOverlayView
        >>> annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = False

        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (#9db8d2, #7590ae)
        Other Calendar (red, blue)
        Another Calendar (timetable) (green, red)
        Interesting Calendar (yellow, white)
        Interesting Calendar (timetable) (yellow, white)

        >>> annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = True

    Only the timetable is overlaid if the user is looking at someone else's
    calendar:

        >>> view = CalendarListView(CalendarStub('Some Calendar'), request)
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        Some Calendar (#9db8d2, #7590ae)
        Some Calendar (timetable) (#9db8d2, #7590ae)

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDailyCalendarRowsView))
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF|
                                                 doctest.NORMALIZE_WHITESPACE))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
