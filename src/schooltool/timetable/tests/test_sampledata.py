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
Unit tests for schooltool.timetable.sampledata

$Id$
"""

import unittest

from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup, ztapi

from schooltool.testing import setup as stsetup


def setUp(test):
    setup.placefulSetUp()
    stsetup.setUpApplicationPreferences()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleTimetableSchema():
    """A sample data plugin that generates a timetable schema

        >>> from schooltool.timetable.sampledata import SampleTimetableSchema
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> from schooltool.app.interfaces import IApplicationPreferences
        >>> plugin = SampleTimetableSchema()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> app = stsetup.setupSchoolToolSite()
        >>> IApplicationPreferences(app).timezone = 'Europe/Vilnius'

    This plugin creates a timetable schema:

        >>> plugin.generate(app, 42)
        >>> len(app['ttschemas'])
        1

    The day ids on the timetable schema and on the timetable model are set:

        >>> schema = app['ttschemas']['simple']
        >>> schema.day_ids
        ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6']
        >>> schema.model.timetableDayIds
        ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6']

    Let's check the slots in the first day template:

        >>> result = []
        >>> for period in schema.model.dayTemplates['Day 1']:
        ...      print period.tstart, period.duration
        08:00:00 0:55:00
        09:00:00 0:55:00
        10:00:00 0:55:00
        11:00:00 0:55:00
        12:30:00 0:55:00
        13:30:00 1:00:00

    The timetable model has schoolday templates for all days in cycle.

        >>> for day in schema.day_ids:
        ...    result = []
        ...    print day,
        ...    for period in schema[day].keys():
        ...         print period,
        ...    print "Homeroom - ", schema[day].homeroom_period_ids[0]
        Day 1 A B C D E F Homeroom -  A
        Day 2 B C D E F A Homeroom -  B
        Day 3 C D E F A B Homeroom -  C
        Day 4 D E F A B C Homeroom -  D
        Day 5 E F A B C D Homeroom -  E
        Day 6 F A B C D E Homeroom -  F

    The default timetable schema is set:

        >>> app['ttschemas'].getDefault()
        <schooltool.timetable.schema.TimetableSchema object at ...>

    The schema's timezone is correctly set from the app preferences:

        >>> schema.timezone
        'Europe/Vilnius'

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
