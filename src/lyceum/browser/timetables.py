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
Lyceum person browser views.

$Id$
"""
from datetime import datetime
from pytz import utc

from zope.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.i18n import translate

from schooltool.timetable.interfaces import ICompositeTimetables
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.timetable.interfaces import ITimetables
from schooltool.timetable.interfaces import ITimetableCalendarEvent

from schooltool import SchoolToolMessage as _


class PersonTimetableView(BrowserView):

    template = ViewPageTemplateFile('templates/timetable.pt')

    def __call__(self):
        return self.template()

    def term_id(self):
        dt = datetime.utcnow()
        date = utc.localize(dt).date()
        terms = ISchoolToolApplication(None)["terms"]
        for term_id, term in terms.items():
            if date in term:
                return term_id
        else:
            return None

    @property
    def schooltt_ids(self):
        if not self.context.gradeclass:
            return ['i-ii-kursui', 'iii-iv-kursui']
        elif self.context.gradeclass[0] in '12':
            return ['i-ii-kursui']
        elif self.context.gradeclass[0] in '34':
            return ['iii-iv-kursui']
        else:
            return ['i-ii-kursui', 'iii-iv-kursui']

    def collectTimetableSourceObjects(self):
        ct = ICompositeTimetables(self.context)
        return ct.collectTimetableSourceObjects()

    def makeCompositeTimetable(self):
        school_timetables = ISchoolToolApplication(None)['ttschemas']
        composite_timetable = school_timetables[self.schooltt_ids[0]].createTimetable()
        for object in self.collectTimetableSourceObjects():
            ttables = removeSecurityProxy(ITimetables(object).timetables)
            for id in self.schooltt_ids:
                tt_id = "%s.%s" % (self.term_id(), id)
                if tt_id in ttables:
                    for day, period, activity in ttables[tt_id].activities():
                        composite_timetable[day].add(period, activity, send_events=False)
        return composite_timetable

    def days(self):
        composite_timetable = self.makeCompositeTimetable()
        for key in composite_timetable.keys():
            week_day = {}
            week_day['title'] = translate(_(key), context=self.request)
            week_day['periods'] = []
            day = composite_timetable[key]
            for period in day.periods:
                period_dict = {}
                period_dict['title'] = period
                period_dict['activities'] = day[period]
                week_day['periods'].append(period_dict)
            yield week_day

    def rows(self):
        i = self.days()
        return map(None, i, i)


class GroupTimetableView(PersonTimetableView):

    @property
    def schooltt_ids(self):
        if self.context.__name__[0] in '12':
            return ['i-ii-kursui']
        elif self.context.__name__[0] in '34':
            return ['iii-iv-kursui']
        else:
            return ['i-ii-kursui', 'iii-iv-kursui']

    def collectTimetableSourceObjects(self):
        objects = set()
        for person in self.context.members:
            ct = ICompositeTimetables(person)
            for object in ct.collectTimetableSourceObjects():
                objects.add(object)
        return objects


class ResourceTimetableView(PersonTimetableView):

    @property
    def schooltt_ids(self):
        return ['i-ii-kursui', 'iii-iv-kursui']

    def makeCompositeTimetable(self):
        school_timetables = ISchoolToolApplication(None)['ttschemas']
        composite_timetable = school_timetables[self.schooltt_ids[0]].createTimetable()

        for event in ISchoolToolCalendar(self.context):
            if ITimetableCalendarEvent.providedBy(event):
                composite_timetable[event.day_id].add(event.period_id,
                                                      event.activity,
                                                      send_events=False)
        return composite_timetable
