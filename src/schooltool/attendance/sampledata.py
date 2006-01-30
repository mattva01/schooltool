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

from schooltool.attendance.interfaces import IDayAttendance
from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable.interfaces import ITimetables


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
    explanation_rate = 0.50 # Student explains 50% of his absences and tardies
    excuse_rate = 0.50      # 50% of explained tardies/absences are excused
    reject_rate = 0.30      # 30% of explained tardies/absences are rejected

    only_last_n_days = None # Instead of generating attendance data
                            # for the whole term (which is slow),
                            # generate it only for the last N days

    def explainAttendanceRecord(self, ar):
        """Sometimes adds an explaination.

        Chance of the attendance record being explained is set in
        explanation_rate.

        Depending on excuse_rate and reject_rate the explanation is
        either accepted or rejected.
        """
        if self.rng.random() < self.explanation_rate:
            ar.addExplanation("My car broke")
            if self.rng.random() < self.excuse_rate:
                ar.acceptExplanation()
            elif self.rng.random() < self.reject_rate:
                ar.rejectExplanation()

    def generateDayAttendance(self):
        """Generate sample data for day attendance."""
        day_absences = {}
        persons = self.app['persons']
        for day in self.term:
            if day < self.start_date:
                continue
            if day > self.end_date:
                continue
            strdate = day.strftime("%Y-%m-%d")
            if self.term.isSchoolday(day):
                day_absences[strdate] = []
                for person_name in persons:
                    if not person_name.startswith("student"):
                        continue
                    person = persons[person_name]
                    present = self.rng.random() > self.day_absence_rate
                    if not present:
                        day_absences[strdate].append(person_name)
                    IDayAttendance(person).record(day, present)
        transaction.commit()
        return day_absences

    def generateSectionAttendance(self, day_absences):
        """Generate sample data for section attendance."""
        for section in self.app['sections'].values():
            meetings = ITimetables(section).makeTimetableCalendar(self.start_date,
                                                                  self.end_date)
            for meeting in meetings:
                for student in section.members:
                    attendance = ISectionAttendance(student)
                    present = self.rng.random() > self.absence_rate

                    datestr = meeting.dtstart.strftime("%Y-%m-%d")
                    day_absence = (datestr in day_absences and
                                   student.__name__ in day_absences[datestr])
                    if day_absence:
                        present = False

                    attendance.record(section, meeting.dtstart,
                                      meeting.duration, meeting.period_id,
                                      present)
                    ar = attendance.get(section, meeting.dtstart)

                    if not present and not day_absence:
                        if self.rng.random() < self.tardy_rate:
                            ar.makeTardy(meeting.dtstart + datetime.timedelta(minutes=15))

                    if not present:
                        self.explainAttendanceRecord(ar)

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

        day_absences = self.generateDayAttendance()
        self.generateSectionAttendance(day_absences)
