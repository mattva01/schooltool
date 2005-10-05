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

import random
import datetime

from zope.interface import implements

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.timetable.schema import TimetableSchema, TimetableSchemaDay
from schooltool.timetable.model import SequentialDaysTimetableModel
from schooltool.timetable import SchooldayTemplate, SchooldayPeriod


class SampleTimetableSchema(object):

    implements(ISampleDataPlugin)

    name = 'ttschema'
    dependencies = ()

    def generate(self, app, seed=None):
        day_ids = ['Day %d' % i for i in range(1, 7)]
        period_ids = ['A', 'B', 'C', 'D', 'E', 'F']
        day_template = SchooldayTemplate()
        t, dt = datetime.time, datetime.timedelta
        day_template.add(SchooldayPeriod('A', t(8, 0), dt(minutes=55)))
        day_template.add(SchooldayPeriod('B', t(9, 0), dt(minutes=55)))
        day_template.add(SchooldayPeriod('C', t(10, 0), dt(minutes=55)))
        day_template.add(SchooldayPeriod('D', t(11, 0), dt(minutes=55)))
        day_template.add(SchooldayPeriod('E', t(12, 30), dt(minutes=55)))
        day_template.add(SchooldayPeriod('F', t(13, 30), dt(minutes=60)))
        model = SequentialDaysTimetableModel(day_ids, {None: day_template})
        ttschema = TimetableSchema(day_ids, model=model)
        for day_id in day_ids:
            ttschema[day_id] = TimetableSchemaDay(period_ids)
        app['ttschemas']['simple'] = ttschema
