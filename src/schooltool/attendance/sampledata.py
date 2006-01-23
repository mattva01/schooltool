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

from schooltool.attendance.interfaces import ISectionAttendance
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable.interfaces import ITimetables


class SectionAttendancePlugin(object):
    """Section attendance sample data generator.

    Generates attendance data for the fall term of 2005 only.
    """

    implements(ISampleDataPlugin)

    name = "section_attendance"
    dependencies = ("section_timetables", )

    absence_rate = 0.03     # A student skips 3% of meetings on average
    tardy_rate = 0.90       # A student is late to 90% of abscences on average
    explanation_rate = 0.50 # Student explains 50% of his abscences and tardies
    excuse_rate = 0.50      # 50% of explained tardies/abscences are excused
    reject_rate = 0.30      # 30% of explained tardies/abscences are rejected

    only_last_n_days = None # Instead of generating attendance data
                            # for the whole term (which is slow),
                            # generate it only for the last N days

    def generate(self, app, seed=None):
        rng = random.Random(seed)
        term = app['terms']['2005-fall']

        # interval in which attendance records will be generated
        start_date = term.first
        end_date = term.last
        if self.only_last_n_days:
            start_date = end_date - datetime.timedelta(self.only_last_n_days - 1)

        for section in app['sections'].values():
            # You cannot store proxied objects in the ZODB.  It is safe
            # to unwrap, since only managers can invoke sample data.
            unproxied_section = removeSecurityProxy(section)
            meetings = ITimetables(section).makeTimetableCalendar(start_date,
                                                                  end_date)
            for meeting in meetings:
                for student in section.members:
                    attendance = ISectionAttendance(student)
                    present = rng.random() > self.absence_rate
                    attendance.record(unproxied_section, meeting.dtstart,
                                      meeting.duration, meeting.period_id,
                                      present)
                    if not present:
                        ar = attendance.get(unproxied_section, meeting.dtstart)
                        if rng.random() < self.tardy_rate:
                            ar.makeTardy(meeting.dtstart + datetime.timedelta(minutes=15))

                        if rng.random() < self.explanation_rate:
                            ar.addExplanation("My car broke")
                            if rng.random() < self.excuse_rate:
                                ar.acceptExplanation()
                            elif rng.random() < self.reject_rate:
                                ar.rejectExplanation()

            # The transaction commit keeps the memory usage low, but at a cost
            # of running time and disk space.
            transaction.commit()
