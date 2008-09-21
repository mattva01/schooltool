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

$Id$
"""

import unittest

from zope.testing import doctest
from zope.publisher.browser import TestRequest
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.component import adapts
from zope.interface import implements

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.testing import setup as sbsetup


# def doctest_CalendarSTOverlayView():
#     r"""Tests for CalendarSTOverlayView

#      Some setup:

#         >>> sbsetup.setUpCalendaring()

#         >>> from zope.component import provideAdapter
#         >>> from schooltool.app.app import ShowTimetables
#         >>> provideAdapter(ShowTimetables)

#         >>> from zope.interface import classImplements
#         >>> from zope.annotation.interfaces import IAttributeAnnotatable
#         >>> from schooltool.app.overlay import CalendarOverlayInfo
#         >>> classImplements(CalendarOverlayInfo, IAttributeAnnotatable)

#         >>> from schooltool.timetable.browser.overlay import CalendarSTOverlayView
#         >>> View = SimpleViewClass('../templates/calendar_overlay.pt',
#         ...                        bases=(CalendarSTOverlayView,))

#     CalendarOverlayView is a view on anything.

#         >>> context = object()
#         >>> request = TestRequest()
#         >>> view = View(context, request, None, None)

#     It renders to an empty string unless its context is the calendar of the
#     authenticated user

#         >>> view()
#         u'\n'

#     If you are an authenticated user looking at your own calendar, this view
#     renders a calendar selection portlet.

#         >>> from schooltool.group.group import Group
#         >>> from schooltool.person.person import Person
#         >>> from schooltool.course.course import Course
#         >>> from schooltool.course.section import Section
#         >>> from schooltool.app.security import Principal
#         >>> app = sbsetup.setUpSchoolToolSite()
#         >>> person = app['persons']['whatever'] = Person('fred')
#         >>> group1 = app['groups']['g1'] = Group(title="Group 1")
#         >>> group2 = app['groups']['g2'] = Group(title="Group 2")
#         >>> history = app['courses']['c1'] = Course(title="History")
#         >>> section = app['sections']['s1'] = Section(title="History")
#         >>> history.sections.add(section)

#         >>> from schooltool.course.interfaces import ISection
#         >>> from schooltool.timetable.interfaces import ITimetables
#         >>> class TimetablesStub(object):
#         ...     adapts(ISection)
#         ...     implements(ITimetables)
#         ...     def __init__(self, section):
#         ...         self.section = section
#         ...         self.terms = []
#         ...         self.timetables = {}
#         >>> provideAdapter(TimetablesStub)

#         >>> from schooltool.app.interfaces import IShowTimetables
#         >>> info = person.overlaid_calendars.add(
#         ...     ISchoolToolCalendar(group1), show=True)
#         >>> IShowTimetables(info).showTimetables = False
#         >>> info = person.overlaid_calendars.add(
#         ...     ISchoolToolCalendar(group2), show=False)
#         >>> info = person.overlaid_calendars.add(
#         ...     ISchoolToolCalendar(section), show=False)

#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('id', 'title', person))
#         >>> view = View(ISchoolToolCalendar(person), request, None, None)

#         >>> print view()
#         <div id="portlet-calendar-overlay" class="portlet">
#         ...
#         ...<input type="checkbox" checked="checked" disabled="disabled" />...
#         ...<input type="checkbox" name="my_timetable" />...
#         ...My Calendar...
#         ...
#         ...<input type="checkbox" name="overlay:list"
#                   checked="checked" value="/groups/g1" />...
#         ...<input type="checkbox"
#                   name="overlay_timetables:list"
#                   value="/groups/g1" />...
#         ...
#         ...<input type="checkbox" name="overlay:list"
#                   value="/groups/g2" />...
#         ...<input type="checkbox" name="overlay_timetables:list"
#                   checked="checked" value="/groups/g2" />...
#         ...<td style="width: 100%">Group 2</td>...
#         ...
#         ...<input type="checkbox" name="overlay:list"
#                   value="/sections/s1" />...
#         ...<input type="checkbox" name="overlay_timetables:list"
#                   checked="checked" value="/sections/s1" />...
#         ...<td style="width: 100%"> -- History</td>...
#         ...
#         </div>

#     If the request has 'OVERLAY_APPLY', CalendarOverlayView applies your
#     changes

#         >>> request.form['overlay'] = [u'/groups/g2']
#         >>> request.form['overlay_timetables'] = [u'/groups/g1']
#         >>> request.form['OVERLAY_APPLY'] = u"Apply"
#         >>> print view()
#         <div id="portlet-calendar-overlay" class="portlet">
#         ...
#         ...<input type="checkbox" checked="checked" disabled="disabled" />...
#         ...<input type="checkbox" name="my_timetable" />...
#         ...My Calendar...
#         ...
#         ...<input type="checkbox" name="overlay:list"
#                   value="/groups/g1" />...
#         ...<input type="checkbox"
#                   name="overlay_timetables:list"
#                   checked="checked" value="/groups/g1" />...
#         ...
#         ...<input type="checkbox" name="overlay:list"
#                   checked="checked" value="/groups/g2" />...
#         ...<input type="checkbox" name="overlay_timetables:list"
#                   value="/groups/g2" />...
#         ...
#         </div>

#     It also redirects you to request.URL:

#         >>> request.response.getStatus()
#         302
#         >>> request.response.getHeader('Location')
#         'http://127.0.0.1'

#     There are two reasons for the redirect: first, part of the page template
#     just rendered might have become invalid when calendar overlay selection
#     changed, second, this lets the user refresh the page without having to
#     experience confirmation dialogs that say "Do you want to POST this form
#     again?".

#     If the request has 'OVERLAY_MORE', CalendarOverlayView redirects to
#     calendar_selection.html

#         >>> request = TestRequest()
#         >>> request.setPrincipal(Principal('id', 'title', person))
#         >>> request.form['OVERLAY_MORE'] = u"More..."
#         >>> view = View(ISchoolToolCalendar(person), request, None, None)
#         >>> content = view()
#         >>> request.response.getStatus()
#         302
#         >>> request.response.getHeader('Location')
#         'http://127.0.0.1/persons/fred/calendar_selection.html?nexturl=http%3A//127.0.0.1'

#     """


def doctest_TimetableCalendarListSubscriber(self):
    """Tests for TimetableCalendarListSubscriber.

    This subscriber only has the getCalendars() method.

    This subscriber lists only timetable calendars.  The color of each
    timetable calendar is the same as of the corresponding personal
    calendar.

    Some initial setup:

        >>> sbsetup.setUpCalendaring()

    A handful of useful stubs:

        >>> class CalendarStub:
        ...     def __init__(self, title):
        ...         self.title = title
        ...     def _getParent(self):
        ...         return PersonStub(self.title, self)
        ...     __parent__ = property(_getParent)

        >>> from zope.interface import implements
        >>> from schooltool.app.interfaces import IShowTimetables
        >>> class OverlayInfoStub:
        ...     implements(IShowTimetables)
        ...
        ...     def __init__(self, title, color1, color2,
        ...                  show=True, showTimetables=True):
        ...         self.calendar = CalendarStub(title)
        ...         self.color1 = color1
        ...         self.color2 = color2
        ...         self.show = show
        ...         self.showTimetables = showTimetables

        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.app.interfaces import IHaveCalendar
        >>> from schooltool.app.cal import CALENDAR_KEY
        >>> from zope.interface import implements
        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> from schooltool.timetable.interfaces import ICompositeTimetables
        >>> class PersonStub:
        ...     implements(IAttributeAnnotatable, IHaveCalendar,
        ...                ICompositeTimetables)
        ...     def __init__(self, title, calendar=None):
        ...         self.title = title
        ...         self.__annotations__= {CALENDAR_KEY: calendar}
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

        >>> from schooltool.timetable.browser.overlay import TimetableCalendarListSubscriber
        >>> import calendar as pycalendar
        >>> calendar = CalendarStub('My Calendar')
        >>> request = TestRequest()
        >>> subscriber = TimetableCalendarListSubscriber(calendar, request)
        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (timetable) (#9db8d2, #7590ae)

    If the authenticated user is looking at his own calendar, then
    a list of overlaid calendars is taken into consideration

        >>> from schooltool.person.interfaces import IPerson
        >>> class PrincipalStub:
        ...     def __init__(self):
        ...         self.person = PersonStub('x', calendar=calendar)
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return self.person
        >>> principal = PrincipalStub()
        >>> request.setPrincipal(principal)

        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        Another Calendar (timetable) (green, red)
        Interesting Calendar (timetable) (yellow, white)

    If the person has the current timetable display checked, the composite
    timetable calendar is included in the list:

        >>> from zope.annotation.interfaces import IAnnotations
        >>> annotations = IAnnotations(principal.person)
        >>> from schooltool.timetable.browser.overlay import CalendarSTOverlayView
        >>> annotations[CalendarSTOverlayView.SHOW_TIMETABLE_KEY] = True

        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        My Calendar (timetable) (#9db8d2, #7590ae)
        Another Calendar (timetable) (green, red)
        Interesting Calendar (timetable) (yellow, white)

    Only the timetable is overlaid if the user is looking at someone else's
    calendar:

        >>> subscriber = TimetableCalendarListSubscriber(CalendarStub('Some Calendar'),
        ...                                     request)
        >>> for c, col1, col2 in subscriber.getCalendars():
        ...     print '%s (%s, %s)' % (c.title, col1, col2)
        Some Calendar (timetable) (#9db8d2, #7590ae)

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                            doctest.REPORT_NDIFF|
                                            doctest.NORMALIZE_WHITESPACE))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
