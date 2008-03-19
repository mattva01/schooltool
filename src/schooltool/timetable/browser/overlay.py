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
Calendar overlay views for SchoolTool with timetabling enabled.

$Id$
"""
from zope.traversing.api import getPath, getParent
from zope.annotation.interfaces import IAnnotations
from zope.security.checker import canAccess
from zope.security.proxy import removeSecurityProxy

from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.course.interfaces import ISection
from schooltool.person.interfaces import IPerson
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IShowTimetables
from schooltool.app.browser.overlay import CalendarOverlayView


class CalendarSTOverlayView(CalendarOverlayView):
    """View for the calendar overlay portlet.

    Much like the original CalendarOverlayView in SchoolBell, this view allows
    you to choose calendars to be displayed, but this one allows you to view
    timetables of the calendar owners as well.

    This view can be used with any context, but it gets rendered to an empty
    string unless context is the calendar of the authenticated user.

    Note that this view contains a self-posting form and handles submits that
    contain 'OVERLAY_APPLY' or 'OVERLAY_MORE' in the request.
    """

    SHOW_TIMETABLE_KEY = 'schooltool.app.browser.cal.show_my_timetable'

    def items(self):
        """Return items to be shown in the calendar overlay.

        Does not include "my calendar".

        Each item is a dict with the following keys:

            'title' - title of the calendar, or label for section calendars

            'calendar' - the calendar object

            'color1', 'color2' - colors assigned to this calendar

            'id' - identifier for form controls

            'checked' - was this item checked for display (either "checked" or
            None)?

            'checked_tt' - was this calendar owner's timetable checked for
            display?
        """
        person = IPerson(self.request.principal)
        def getTitleOrLabel(item):
            object = item.calendar.__parent__
            if ISection.providedBy(object):
                section = removeSecurityProxy(object)
                if person in section.instructors:
                    return section.title
                else:
                    return section.label
            else:
                return item.calendar.title

        items = [((item.calendar.title, getPath(item.calendar.__parent__)),
                  {'title': getTitleOrLabel(item),
                   'id': getPath(item.calendar.__parent__),
                   'calendar': item.calendar,
                   'checked': item.show and "checked" or '',
                   'checked_tt':
                       IShowTimetables(item).showTimetables and "checked" or '',
                   'color1': item.color1,
                   'color2': item.color2})
                 for item in person.overlaid_calendars
                 if canAccess(item.calendar, '__iter__')]
        items.sort()
        return [i[-1] for i in items]

    def update(self):
        """Process form submission."""
        if 'OVERLAY_APPLY' in self.request:
            person = IPerson(self.request.principal)
            selected = set(self.request.get('overlay_timetables', []))
            for item in person.overlaid_calendars:
                path = getPath(item.calendar.__parent__)
                # XXX this is related to the issue
                # http://issues.schooltool.org/issue391!
                IShowTimetables(item).showTimetables = path in selected

            # The unproxied object will only be used for annotations.
            person = removeSecurityProxy(person)

            annotations = IAnnotations(person)
            annotations[self.SHOW_TIMETABLE_KEY] = bool('my_timetable'
                                                        in self.request)
        return CalendarOverlayView.update(self)

    def myTimetableShown(self):
        person = IPerson(self.request.principal)
        # The unproxied object will only be used for annotations.
        person = removeSecurityProxy(person)
        annotations = IAnnotations(person)
        return annotations.get(self.SHOW_TIMETABLE_KEY, False)


class TimetableCalendarListSubscriber(object):
    """A subscriber that can tell which calendars should be displayed.

    This subscriber includes composite timetable calendars, overlaid
    calendars and the calendar you are looking at.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def getCalendars(self):
        """Get a list of calendars to display.

        Yields tuples (calendar, color1, color2).
        """
        parent = getParent(self.context)
        ttcalendar = ICompositeTimetables(parent).makeTimetableCalendar()

        user = IPerson(self.request.principal, None)
        if user is None:
            yield (ttcalendar, '#9db8d2', '#7590ae')
            return # unauthenticated user

        unproxied_context = removeSecurityProxy(self.context)
        unproxied_calendar = removeSecurityProxy(ISchoolToolCalendar(user))
        if unproxied_context is not unproxied_calendar:
            yield (ttcalendar, '#9db8d2', '#7590ae')
            return # user looking at the calendar of some other person

        # personal timetable
        unproxied_person = removeSecurityProxy(user) # for annotations
        annotations = IAnnotations(unproxied_person)
        if annotations.get(CalendarSTOverlayView.SHOW_TIMETABLE_KEY, False):
            yield (ttcalendar, '#9db8d2', '#7590ae')
            # Maybe we should change the colour to differ from the user's
            # personal calendar?

        for item in user.overlaid_calendars:
            if canAccess(item.calendar, '__iter__'):
                # overlaid timetables
                if IShowTimetables(item).showTimetables:
                    owner = item.calendar.__parent__
                    ttcalendar = ICompositeTimetables(owner).makeTimetableCalendar()
                    yield (ttcalendar, item.color1, item.color2)
