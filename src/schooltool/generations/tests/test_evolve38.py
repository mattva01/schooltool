#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve38
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.component import provideHandler, provideAdapter
from zope.component.hooks import getSite, setSite
from zope.interface import implements
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.site.folder import Folder

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.generations.tests import ContextStub
from schooltool.timetable.app import SCHEDULES_KEY
from schooltool.timetable.app import TIMETABLES_KEY
from schooltool.timetable.app import SchoolToolSchedules
from schooltool.timetable.schedule import Schedule, ScheduleContainer
from schooltool.timetable.timetable import Timetable, SelectedPeriodsSchedule


class AppStub(Folder):
    implements(ISchoolToolApplication)

    def __init__(self):
        super(AppStub, self).__init__()


def doctest_evolve38():
    r"""Test evolution to generation 38.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()
        >>> manager = setup.createSiteManager(app)

        >>> schedules = app[SCHEDULES_KEY] = SchoolToolSchedules()
        >>> timetables = app[TIMETABLES_KEY] = SchoolToolSchedules()

        >>> events = []
        >>> def log_event(event):
        ...     events.append('%s: %s / %s' %
        ...         (event.__class__.__name__,
        ...          event.object.__parent__.__name__,
        ...          event.object.__name__))
        >>> provideHandler(log_event, [IObjectModifiedEvent])

        >>> provideAdapter(lambda ignore:app, (None,), ISchoolToolApplication)


    Let's build two timetables.

        >>> tt1 = timetables['1'] = Timetable('starts', 'ends')
        >>> tt2 = timetables['2'] = Timetable('starts', 'ends')

    Add schedule container that does not use them.

        >>> schedules['0'] = ScheduleContainer()
        >>> schedules['0']['1'] = Schedule('starts', 'ends')

    And some containers that do use the timetables.

        >>> schedules['1'] = ScheduleContainer()
        >>> schedules['1']['1'] = SelectedPeriodsSchedule(tt1, 'starts', 'ends')
        >>> schedules['2'] = ScheduleContainer()
        >>> schedules['2']['1'] = SelectedPeriodsSchedule(tt2, 'starts', 'ends')
        >>> schedules['2']['2'] = SelectedPeriodsSchedule(tt2, 'starts', 'ends')

        >>> events[:] = []

    Let's evolve now.

        >>> from schooltool.generations.evolve38 import evolve
        >>> evolve(context)

    ObjectModifiedEvent was fired for each of schedule containers
    that have schedules using any of app's timetables.

        >>> print '\n'.join(events)
        ObjectModifiedEvent: schooltool.timetable.schedules / 1
        ObjectModifiedEvent: schooltool.timetable.schedules / 2

    Site was restored after evolution.

        >>> print getSite()
        None

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpTraversal()
    setSite()

def tearDown(test):
    setSite()
    setup.placelessTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
