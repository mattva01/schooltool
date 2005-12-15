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
Timetable sample data generation

$Id$
"""

import datetime

from zope.interface import implements

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable import SchooldayTemplate, SchooldaySlot
from schooltool.timetable.schema import TimetableSchema, TimetableSchemaDay
from schooltool.timetable.model import SequentialDayIdBasedTimetableModel
from schooltool.timetable.term import Term


class SampleTimetableSchema(object):

    implements(ISampleDataPlugin)

    name = 'ttschema'
    dependencies = ()

    def generate(self, app, seed=None):
        day_ids = ['Day %d' % i for i in range(1, 7)]
        period_ids = ['A', 'B', 'C', 'D', 'E', 'F']
        t, dt = datetime.time, datetime.timedelta
        slots = [(t(8, 0), dt(minutes=55)),
                 (t(9, 0), dt(minutes=55)),
                 (t(10, 0), dt(minutes=55)),
                 (t(11, 0), dt(minutes=55)),
                 (t(12, 30), dt(minutes=55)),
                 (t(13, 30), dt(minutes=60))]

        day_templates = {}
        for day_idx, day_id in enumerate(day_ids):
            day_template = SchooldayTemplate()
            for idx, (tstart, duration) in enumerate(slots):
                day_template.add(SchooldaySlot(tstart, duration))
            day_templates[day_id] = day_template

        model = SequentialDayIdBasedTimetableModel(day_ids, day_templates)
        ttschema = TimetableSchema(day_ids, model=model)
        for idx, day_id in enumerate(day_ids):
            periods = period_ids[idx:] + period_ids[:idx]
            ttschema[day_id] = TimetableSchemaDay(periods)
        app['ttschemas']['simple'] = ttschema


class SampleTerms(object):
    implements(ISampleDataPlugin)

    name = 'terms'
    dependencies = ()

    def generate(self, app, seed=None):
        date = datetime.date
        fall = Term('2005-fall', date(2005, 8, 22), date(2005, 12, 23))
        fall.addWeekdays(0, 1, 2, 3, 4)
        app['terms']['2005-fall'] = fall

        spring = Term('2006-spring', date(2006, 1, 26), date(2006, 5, 31))
        spring.addWeekdays(0, 1, 2, 3, 4)
        app['terms']['2006-spring'] = spring
