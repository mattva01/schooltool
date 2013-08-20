#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
SchoolTool timetable integration.
"""

from persistent.list import PersistentList
import zope.lifecycleevent
from zope.interface import implements
from zope.component import adapts

from schooltool.common import DateRange
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISubscriber
from schooltool.schoolyear.subscriber import EventAdapterSubscriber
from schooltool.term.term import getTermForDate, EmergencyDayEvent
from schooltool.timetable.interfaces import ITimetableContainer
from schooltool.timetable.interfaces import IScheduleExceptions
from schooltool.timetable.schedule import MeetingException


class EmergencyDayTimetableSubscriber(EventAdapterSubscriber):
    adapts(EmergencyDayEvent)
    implements(ISubscriber)

    def __call__(self):
        term = getTermForDate(self.event.date)
        if term is None:
            return
        old_date = self.event.date
        new_date = self.event.replacement_date
        schoolyear = ISchoolYear(term)
        timetables = ITimetableContainer(schoolyear)
        for timetable in timetables.values():
            if IScheduleExceptions.providedBy(timetable):
                modified = False
                scheduled = DateRange(timetable.first, timetable.last)
                meeting_exceptions = PersistentList()
                if old_date in scheduled:
                    meetings = list(timetable.iterMeetings(old_date))
                    for meeting in meetings:
                        meeting_exceptions.append(
                            MeetingException(
                                meeting.dtstart.replace(year=new_date.year,
                                                        month=new_date.month,
                                                        day=new_date.day),
                                meeting.duration,
                                period=meeting.period,
                                meeting_id=meeting.meeting_id))
                    timetable.exceptions[old_date] = PersistentList()
                    modified = True
                if new_date in scheduled:
                    timetable.exceptions[new_date] = meeting_exceptions
                    modified = True
                if modified:
                    zope.lifecycleevent.modified(timetable)
