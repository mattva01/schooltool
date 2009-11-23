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
from zope.component import getUtility
from zope.proxy import sameProxiedObjects
from zope.traversing.api import getPath, getParent
from zope.annotation.interfaces import IAnnotations
from zope.security.checker import canAccess
from zope.security.proxy import removeSecurityProxy

from schooltool.term.interfaces import ITerm
from schooltool.term.interfaces import IDateManager
from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.course.interfaces import ISection
from schooltool.person.interfaces import IPerson
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import IShowTimetables
from schooltool.app.browser.overlay import CalendarOverlayView


class CalendarSTOverlayView(CalendarOverlayView):
    """View for the calendar overlay portlet.

    Much like the original CalendarOverlayView in SchoolTool, this view allows
    you to choose calendars to be displayed, but this one allows you to view
    timetables of the calendar owners as well.

    This view can be used with any context, but it gets rendered to an empty
    string unless context is the calendar of the authenticated user.

    Note that this view contains a self-posting form and handles submits that
    contain 'OVERLAY_APPLY' or 'OVERLAY_MORE' in the request.
    """

    SHOW_TIMETABLE_KEY = 'schooltool.app.browser.cal.show_my_timetable'

    def split_overlaid_calendars(self):
        person = IPerson(self.request.principal)
        section_items = []
        non_section_items = []

        for item in person.overlaid_calendars:
            if ISection.providedBy(item.calendar.__parent__):
                section_items.append(item)
            else:
                non_section_items.append(item)

        return section_items, non_section_items

    def get_scheduled_terms(self, section_items):
        terms = set()
        for item in section_items:
            terms.add(ITerm(removeSecurityProxy(item.calendar.__parent__)))
        terms = [{'term': term,
                  'items': []} for term in terms]
        return sorted(terms, key=lambda t: t['term'].last, reverse=True)

    def populate_terms(self, section_items):
        terms = self.get_scheduled_terms(section_items)
        if not terms:
            return [], []

        current_term = getUtility(IDateManager).current_term
        for term in terms:
            for item in section_items:
                if sameProxiedObjects(term['term'],
                                      ITerm(item.calendar.__parent__)):
                    term['items'].append(item)
            term['expanded'] = sameProxiedObjects(term['term'], current_term)

        try:
            last_expanded = (n for n, item in enumerate(terms)
                             if item['expanded']).next()
            return terms[:last_expanded+1], terms[last_expanded+1:]
        except StopIteration:
            return terms, []

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

        def getTitleOrLabel(obj):
            obj = removeSecurityProxy(obj)
            if ISection.providedBy(obj):
                if person in obj.instructors:
                    return obj.title
                else:
                    return obj.label
            else:
                return obj.title

        section_items, non_section_items = self.split_overlaid_calendars()
        groups, more_groups = self.populate_terms(section_items)

        items = {}

        def make_overlay_item(item):
            obj = item.calendar.__parent__
            return ((item.calendar.title, getPath(obj)),
                    {'title': getTitleOrLabel(obj),
                     'id': getPath(obj),
                     'calendar': item.calendar,
                     'checked': item.show,
                     'checked_tt': IShowTimetables(item).showTimetables,
                     'color1': item.color1,
                     'color2': item.color2})

        def itemize(items):
            overlays = sorted([make_overlay_item(item)
                               for item in items
                               if canAccess(item.calendar, '__iter__')])
            return [overlay
                    for key, overlay in overlays]

        items['items'] = itemize(non_section_items)
        items['groups'] = [{'title': group['term'].title,
                            'items': itemize(group['items'])}
                           for group in groups]
        items['more_groups'] = [{'title': group['term'].title,
                                 'items': itemize(group['items'])}
                                for group in more_groups]
        return items

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
