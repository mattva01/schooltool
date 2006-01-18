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

    absence_rate = 0.01     # A student skips 1% of meetings on average

    def generate(self, app, seed=None):
        rng = random.Random(seed)
        term = app['terms']['2005-fall']
        for section in app['sections'].values():
            # You cannot store proxied objects in the ZODB.  It is safe
            # to unwrap, since only managers can invoke sample data.
            unproxied_section = removeSecurityProxy(section)
            meetings = ITimetables(section).makeTimetableCalendar(term.first,
                                                                  term.last)
            for meeting in meetings:
                for student in section.members:
                    attendance = ISectionAttendance(student)
                    present = rng.random() > self.absence_rate
                    attendance.record(unproxied_section, meeting.dtstart,
                                      meeting.duration, meeting.period_id,
                                      present)
            # The transaction commit keeps the memory usage low, but at a cost
            # of running time and disk space.
            transaction.commit()
