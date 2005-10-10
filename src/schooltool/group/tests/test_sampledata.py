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
Unit tests for schooltool.person.sampledata

$Id$
"""

import unittest
from datetime import datetime, timedelta

from pytz import utc
from zope.interface.verify import verifyObject
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing import setup as stsetup
from schooltool.relationship.tests import setUpRelationships
from schooltool.app.cal import getCalendar
from schooltool.timetable.term import getTermForDate


def setUp(test):
    setup.placefulSetUp()
    stsetup.setupCalendaring()


def tearDown(test):
    setup.placefulTearDown()


def doctest_SampleGroups():
    """A sample data plugin that generates groups and events for groups

        >>> from schooltool.group.sampledata import SampleGroups
        >>> from schooltool.sampledata.interfaces import ISampleDataPlugin
        >>> plugin = SampleGroups()
        >>> verifyObject(ISampleDataPlugin, plugin)
        True

        >>> plugin.dependencies
        ('students', 'terms')

    Prepare students.
    
        >>> setUpRelationships()
        >>> app = stsetup.setupSchoolToolSite()
        >>> from schooltool.person.sampledata import SampleStudents
        >>> from schooltool.timetable.sampledata import SampleTerms
        >>> studentsPlugin = SampleStudents()
        >>> studentsPlugin.generate(app, 42)
        >>> termsPlugin = SampleTerms()
        >>> termsPlugin.generate(app, 42)

    This plugin creates n_groups groups with n_members_in_group members each.

        >>> old_len = len(app['groups'])

        >>> plugin.generate(app, 42)

        >>> assert len(app['groups']) - old_len == plugin.n_groups

        >>> result = []
        >>> for i in range(plugin.n_groups):
        ...     result.append(app['groups']['group%02d' % i].title)
        >>> result.sort()
        >>> for i in range(5):
        ...     print result[i]
        Aikido
        Basketball
        Cart racing
        Cheerleading
        Chess club
    
    Every group has n_members_in_group student members.

        >>> for i in range(plugin.n_groups):
        ...     n_members = len(app['groups']['group%02d' % i].members) 
        ...     assert n_members == plugin.n_members_in_group

    No student is in more than one group.

        >>> student_ids = [id for id in app['persons'].keys() 
        ...                if id.startswith('student')]
        >>> for student_id in student_ids:
        ...     assert len(app['persons'][student_id].groups) <= 1

    Each group has meeting during 15:00-17:00 as recuring event.
    All meetings happen on schooldays.

        >>> for i in range(plugin.n_groups):
        ...     calendar = getCalendar(app['groups']['group%02d' % i])
        ...     assert len(calendar) == 1
        ...     start = list(calendar)[0].dtstart.date()
        ...     term = getTermForDate(start)
        ...     first = datetime(term.first.year,
        ...                      term.first.month,
        ...                      term.first.day,
        ...                      tzinfo=utc)
        ...     last = datetime(term.last.year,
        ...                     term.last.month,
        ...                     term.last.day,
        ...                     tzinfo=utc)
        ...     for event in calendar:
        ...         assert event.dtstart.strftime('%H:%M:%S') == '15:00:00'
        ...         assert str(event.duration) == '2:00:00'
        ...         assert event.recurrence is not None
        ...     allDates = [ev.dtstart.date()
        ...                 for ev in calendar.expand(first, last)]
        ...     for eventDate in allDates:
        ...         assert term.isSchoolday(eventDate)

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
