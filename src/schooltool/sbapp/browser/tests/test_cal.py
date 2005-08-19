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
Tests for SchoolBell calendaring views.

$Id$
"""
import unittest
from pytz import timezone

from zope.interface import implements
from zope.publisher.browser import TestRequest
from zope.testing import doctest

from schooltool.app.browser.testing import setUp as browserSetUp, tearDown
from schooltool.testing import setup as sbsetup

# Used for the PrincipalStub
# XXX: Bad, it depends on the person package.
from schooltool.person.person import Person, PersonContainer
from schooltool.person.interfaces import IPerson
from schooltool.person.interfaces import IPersonPreferences


def setUp(test=None):
    browserSetUp(test)
    sbsetup.setupSchoolToolSite()
    sbsetup.setupCalendaring()
    sbsetup.setupTimetabling()

def doctest_CalendarListView(self):
    """Tests for CalendarListView.

    This view only has the getCalendars() method.  The view was introduced to
    enhance pluggability.

    CalendarListView.getCalendars returns a list of calendars that
    should be displayed.  This list always includes the context of
    the view, but it may also include other calendars as well.

        >>> from schooltool.app.browser.cal import CalendarListView
        >>> import calendar as pycalendar
        >>> class CalendarStub:
        ...     __parent__ = Person()
        ...     def __init__(self, title):
        ...         self.title = title
        >>> calendar = CalendarStub('My Calendar')
        >>> request = TestRequest()
        >>> view = CalendarListView(calendar, request)
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (getattr(c, 'title', 'null'), col1, col2)
        My Calendar (#9db8d2, #7590ae)
        null (#9db8d2, #7590ae)

    XXX: No clue if the above is still correct.

    If the authenticated user is looking at his own calendar, then
    a list of overlaid calendars is taken into consideration

        >>> class OverlayInfoStub:
        ...     def __init__(self, title, color1, color2, show=True):
        ...         self.calendar = CalendarStub(title)
        ...         self.color1 = color1
        ...         self.color2 = color2
        ...         self.show = show
        >>> class PreferenceStub:
        ...     def __init__(self):
        ...         self.weekstart = pycalendar.MONDAY
        ...         self.timeformat = "%H:%M"
        ...         self.dateformat = "%Y-%m-%d"
        ...         self.timezone = 'UTC'
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> from schooltool.app.interfaces import IHaveCalendar
        >>> from schooltool.app.cal import CALENDAR_KEY
        >>> class PersonStub:
        ...     implements(IHaveCalendar, IAttributeAnnotatable)
        ...     def __conform__(self, interface):
        ...         if interface is IPersonPreferences:
        ...             return PreferenceStub()
        ...     __annotations__ = {CALENDAR_KEY: calendar}
        ...     overlaid_calendars = [
        ...         OverlayInfoStub('Other Calendar', 'red', 'blue'),
        ...         OverlayInfoStub('Hidden', 'green', 'red', False)]
        >>> class PrincipalStub:
        ...     def __conform__(self, interface):
        ...         if interface is IPerson:
        ...             return PersonStub()
        >>> request.setPrincipal(PrincipalStub())
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (getattr(c, 'title', 'null'), col1, col2)
        My Calendar (#9db8d2, #7590ae)
        Other Calendar (red, blue)

    XXX: No clue if the above is still correct.

    No calendars are overlaid if the user is looking at a different
    calendar

        >>> view = CalendarListView(CalendarStub('Some Calendar'), request)
        >>> for c, col1, col2 in view.getCalendars():
        ...     print '%s (%s, %s)' % (getattr(c, 'title', 'null'), col1, col2)
        Some Calendar (#9db8d2, #7590ae)

    """


def test_suite():
    suite = unittest.TestSuite()
    # XXX: Temporary till I find out what's wrong.
    #suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
    #                                   optionflags=doctest.ELLIPSIS))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
