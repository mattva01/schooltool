#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Attendance sample data generation.

$Id$
"""
__docformat__ = 'reStructuredText'

import random
import datetime

import transaction
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.attendance.interfaces import IHomeroomAttendance
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable.interfaces import ICompositeTimetables


class SampleAttendancePlugin(object):
    """Section and day attendance sample data generator.

    Generates attendance data for the fall term of 2005 only.
    """

    implements(ISampleDataPlugin)

    name = "attendance"
    dependencies = ("section_timetables", )

    term_to_use = '2005-fall'

    day_absence_rate = 0.15 # A student skips 15% of days on average

    absence_rate = 0.03     # A student skips 3% of meetings on average
    tardy_rate = 0.90       # A student is late to 90% of absences on average
    explanation_rate = 0.80 # Student explains 80% of his absences and tardies
    excuse_rate = 0.80      # 80% of explained tardies/absences are excused
    reject_rate = 0.30      # 30% of explained tardies/absences are rejected

    only_last_n_days = 14   # Instead of generating attendance data
                            # for the whole term (which is slow),
                            # generate it only for the last N days

    def applyExplanation(self, ar, (explained, processed, accepted)):
        if explained:
            ar.addExplanation("My car broke!")
        if accepted:
            ar.acceptExplanation('001')
        elif processed:
            ar.rejectExplanation()

    def generateExplanation(self):
        explained = False
        processed = False
        accepted = False
        if self.rng.random() < self.explanation_rate:
            explained = True
            if self.rng.random() < self.excuse_rate:
                processed = True
                accepted = True
            elif self.rng.random() < self.reject_rate:
                processed = True
                accepted = False
        return (explained, processed, accepted)

    def generateHomeroomAttendanceDay(self):
        day = {}
        persons = self.app['persons']
        for person_name in persons:
            if not person_name.startswith("student"):
                continue
            person = persons[person_name]
            present = self.rng.random() > self.day_absence_rate

            if not present:
                day[person_name] = self.generateExplanation()
        return day

    def generateHomeroomAttendance(self):
        """Generate sample data for homeroom attendance."""
        hr_absences = {}
        persons = self.app['persons']
        for day in self.term:
            if day < self.start_date:
                continue
            if day > self.end_date:
                continue

            strdate = day.strftime("%Y-%m-%d")
            if self.term.isSchoolday(day):
                hr_absences[strdate] = self.generateHomeroomAttendanceDay()
        return hr_absences

    def generateSectionAttendance(self, hr_absences):
        """Generate sample data for section attendance."""
        for section in self.app['sections'].values():
            meetings = ICompositeTimetables(section).makeTimetableCalendar(self.start_date,
                                                                           self.end_date)
            for meeting in meetings:

                timetable = meeting.activity.timetable
                homeroom_period_ids = timetable[meeting.day_id].homeroom_period_ids
                homeroom = (meeting.period_id in homeroom_period_ids)

                for student in section.members:

                    present = self.rng.random() > self.absence_rate
                    tardy = self.rng.random() < self.tardy_rate

                    datestr = meeting.dtstart.strftime("%Y-%m-%d")
                    hr_absence = (datestr in hr_absences and
                                  student.__name__ in hr_absences[datestr])

                    if hr_absence:
                        present = False
                        hr_explanation = hr_absences[datestr][student.__name__]
                    elif homeroom and not tardy:
                        present = True

                    if not present and not hr_absence:
                        explanation = self.generateExplanation()

                    def recordStatus(attendance):
                        attendance.record(section, meeting.dtstart,
                                          meeting.duration, meeting.period_id,
                                          present)
                        record = attendance.get(section, meeting.dtstart)
                        if hr_absence:
                            self.applyExplanation(record, hr_explanation)
                        return record

                    attendances = [ISectionAttendance(student)]
                    if homeroom:
                        attendances.append(IHomeroomAttendance(student))

                    for attendance in attendances:
                        ar = recordStatus(attendance)
                        if not present and not hr_absence:
                            if tardy:
                                ar.makeTardy(meeting.dtstart + datetime.timedelta(minutes=15))
                            self.applyExplanation(ar, explanation)

            # The transaction commit keeps the memory usage low, but at a cost
            # of running time and disk space.
            transaction.commit()

    def generate(self, app, seed=None):
        # You cannot store proxied objects in the ZODB.  It is safe to
        # unwrap, since only managers can invoke sample data.
        self.app = removeSecurityProxy(app)
        self.rng = random.Random(seed)
        self.term = app['terms'][self.term_to_use]

        # interval in which attendance records will be generated
        self.start_date = self.term.first
        self.end_date = self.term.last
        if self.only_last_n_days:
            timedelta = datetime.timedelta(self.only_last_n_days - 1)
            self.start_date = self.end_date - timedelta

        hr_absences = self.generateHomeroomAttendance()
        self.generateSectionAttendance(hr_absences)
