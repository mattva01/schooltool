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
Group sample data generation

$Id$
"""

import random
from datetime import datetime, timedelta

from pytz import utc
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.calendar.recurrent import DailyRecurrenceRule
from schooltool.calendar.recurrent import WeeklyRecurrenceRule
from schooltool.calendar.recurrent import MonthlyRecurrenceRule
from schooltool.group.group import Group
from schooltool.app.cal import CalendarEvent
from schooltool.app.interfaces import ISchoolToolCalendar


class SampleGroups(object):
    """Sample data generation plugin that creates groups.

    It also adds existing persons as members to the groups, and creates
    group-wide calendar events.
    """

    implements(ISampleDataPlugin)

    name = 'groups'
    dependencies = ('students', 'terms')

    group_titles = ('Marching band', 'Swing chorus', 'Chess club',
                    'Dungeons and Dragons club', 'Jazz dance',
                    'Newspaper', 'Yearbook', 'Basketball',
                    'Swimming', 'Gymnastics', 'Drama',
                    'Computer club', 'Hip-Hop', 'Greenpeace',
                    'Sewing', 'Scouts', 'Cart racing',
                    'ST radio', 'Cheerleading', 'Aikido')
    n_members_in_group = 20
    n_groups = property(lambda self: len(self.group_titles))

    def generate(self, app, seed=None):
        self.random = random.Random(seed)
        n_members = self.n_groups * self.n_members_in_group

        student_ids = [id for id in app['persons'].keys()
                       if id.startswith('student')]
        assert len(student_ids) >= n_members
        member_ids = self.random.sample(student_ids, n_members)
        member_iter = iter(member_ids)

        groups = app['groups']
        for i, title in enumerate(self.group_titles):
            group = groups['group%02d' % i] = Group(title=title)

            # Members
            for count in range(self.n_members_in_group):
                member_id = member_iter.next()
                student = removeSecurityProxy(app['persons'][member_id])
                group.members.add(student)

            # Add meeting event
            recurrenceRule = self.random.choice((DailyRecurrenceRule,
                                                 WeeklyRecurrenceRule,
                                                 MonthlyRecurrenceRule))
            terms = removeSecurityProxy(app['terms'].values())
            term = self.random.choice(terms)
            eventDate = term.first
            recurrence = recurrenceRule(until=term.last)
            meeting = CalendarEvent(
                datetime(eventDate.year, eventDate.month, eventDate.day,
                         15, 00, tzinfo=utc),
                timedelta(hours=2), 'Meeting',
                recurrence=recurrence)
            dates = recurrence.apply(meeting, term.first, term.last)
            exceptions = []
            for recurrDate in dates:
                if not term.isSchoolday(recurrDate):
                    exceptions.append(recurrDate)
            meeting.recurrence = recurrence.replace(exceptions=exceptions)
            calendar = ISchoolToolCalendar(group)
            calendar.addEvent(meeting)

