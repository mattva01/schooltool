#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Unit tests for the schooltool.booking module.

$Id$
"""

import unittest
import datetime

from schooltool.tests.utils import AppSetupMixin


class TestTimetableResourceSynchronizer(AppSetupMixin,
                                         unittest.TestCase):
    """Tests for TimetableResourceSynchronizer."""

    def setUp(self):
        from schooltool.timetable import Timetable
        from schooltool.timetable import TimetableDay
        from schooltool.timetable import TimetableActivity
        self.setUpSampleApp()
        tt = Timetable(['Day 1', 'Day 2'])
        tt['Day 1'] = TimetableDay(['A', 'B'])
        tt['Day 2'] = TimetableDay(['C', 'D'])
        self.tt = tt
        self.person.timetables['2004-fall', 'simple'] = tt.cloneEmpty()
        self.resource.timetables['2004-fall', 'simple'] = tt.cloneEmpty()
        self.location.timetables['2004-fall', 'simple'] = tt.cloneEmpty()
        act = TimetableActivity('Math', owner=self.person,
                                resources=[self.resource, self.location])
        # Events are not hooked up at this point
        for obj in (self.person, self.resource, self.location):
            obj.timetables['2004-fall', 'simple']['Day 1'].add('A', act)

    def test_activity_added(self):
        from schooltool.booking import TimetableResourceSynchronizer
        from schooltool.timetable import TimetableActivity
        from schooltool.interfaces import IEvent
        ttes = TimetableResourceSynchronizer()
        self.app.eventService.subscribe(ttes, IEvent)

        activity = TimetableActivity(title="New", owner=self.person,
                                     resources=(self.location, ))

        ttday = self.person.timetables['2004-fall', 'simple']['Day 1']
        ttday.add('B', activity) # should fire ActivityAddedEvent

        loc_ttday = self.location.timetables['2004-fall', 'simple']['Day 1']
        self.assert_(list(loc_ttday['B']))

        act = list(ttday['B'])[0]
        act2 = list(loc_ttday['B'])[0]
        self.assert_(act2 is act)
        self.assertEquals(act2, activity)

        # TODO: ActivityRemovedEvent

    def test_exception_added_then_removed(self):
        from schooltool.booking import TimetableResourceSynchronizer
        from schooltool.timetable import TimetableException
        from schooltool.timetable import ExceptionalTTCalendarEvent
        from schooltool.interfaces import IEvent

        # Prepare test fixture
        ttes = TimetableResourceSynchronizer()
        self.app.eventService.subscribe(ttes, IEvent)
        tt = self.person.timetables['2004-fall', 'simple']
        rtt = self.resource.timetables['2004-fall', 'simple']
        ltt = self.location.timetables['2004-fall', 'simple']
        act = tt.itercontent().next()[-1]

        # Part 1: add the exception
        exc = TimetableException(datetime.date(2004, 11, 02), 'A', act)
        rtt.exceptions.append(exc)       # Sends out an event

        # TimetableResourceSynchronizer notices the event and adds the
        # exception to the timetables of all resources and persons.  It
        # takes care not to add the exception to a list if it is already
        # in the list.
        self.assertEquals(tt.exceptions, [exc])
        self.assertEquals(rtt.exceptions, [exc])
        self.assertEquals(ltt.exceptions, [exc])

        # Make sure that the object is shared, as it may be edited in place
        exc.replacement = ExceptionalTTCalendarEvent(
                datetime.date(2004, 11, 02), datetime.timedelta(45), "Math",
                exception=exc)
        self.assertEquals(tt.exceptions, [exc])
        self.assertEquals(rtt.exceptions, [exc])
        self.assertEquals(ltt.exceptions, [exc])

        # Part 2: remove the exception
        ltt.exceptions.remove(exc)      # Sends out the event

        # TimetableResourceSynchronizer notices the event and adds the
        # exception to the timetables of all resources and persons.
        self.assertEquals(tt.exceptions, [])
        self.assertEquals(rtt.exceptions, [])
        self.assertEquals(ltt.exceptions, [])

    def test_timetable_replaced(self):
        from schooltool.booking import TimetableResourceSynchronizer
        from schooltool.timetable import TimetableActivity
        from schooltool.timetable import TimetableException
        from schooltool.interfaces import IEvent

        # Prepare test fixture
        ttes = TimetableResourceSynchronizer()
        self.app.eventService.subscribe(ttes, IEvent)
        tt = self.person.timetables['2004-fall', 'simple']
        act = tt.itercontent().next()[-1]
        exc = TimetableException(datetime.date(2004, 11, 02), 'A', act)
        tt.exceptions.append(exc)

        tt = self.person.timetables['2004-fall', 'simple']
        rtt = self.resource.timetables['2004-fall', 'simple']
        ltt = self.location.timetables['2004-fall', 'simple']
        self.assertEquals(tt.exceptions, [exc])
        self.assertEquals(rtt.exceptions, [exc])
        self.assertEquals(ltt.exceptions, [exc])

        # Prepare a new timetable
        new_tt = tt.cloneEmpty()
        new_act = TimetableActivity('Lunch', owner=self.person,
                                    resources=[self.resource])
        new_tt['Day 2'].add('C', new_act)
        new_exc = TimetableException(datetime.date(2004, 11, 03), 'C', new_act)
        new_tt.exceptions.append(new_exc)

        # Replace the timetable (sends out an event)
        self.person.timetables['2004-fall', 'simple'] = new_tt

        tt = self.person.timetables['2004-fall', 'simple']
        rtt = self.resource.timetables['2004-fall', 'simple']
        ltt = self.location.timetables['2004-fall', 'simple']
        self.assertEquals(tt.exceptions, [new_exc])
        self.assertEquals(rtt.exceptions, [new_exc])
        self.assertEquals(ltt.exceptions, [])
        self.assert_(new_act in tt['Day 2']['C'])
        self.assert_(new_act in rtt['Day 2']['C'])

        # Remove the timetable (sends out an event)
        #   Catches two bugs:
        #     - the code did not check for a event.new_timetable being None
        #     - the code did not catch KeyErrors when a timetable was gone
        del self.person.timetables['2004-fall', 'simple']
        self.assertEquals(rtt.exceptions, [])
        self.assertEquals(ltt.exceptions, [])
        self.assertEquals(list(rtt['Day 2']['C']), [])

        # Add a timetable (sends out an event)
        #   Catches a bug:
        #     - the code did not check for a event.old_timetable being None
        self.person.timetables['2004-fall', 'simple'] = self.tt.cloneEmpty()

        # Test activity replication:
        #    changing the timetable of a resource must change owner's timetable
        #    self.person has no timetable -- it must be created
        del self.person.timetables['2004-fall', 'simple']
        new_tt = tt.cloneEmpty()
        new_act = TimetableActivity('Supper', owner=self.person,
                                    resources=[self.resource])
        new_tt['Day 1'].add('A', new_act)
        self.resource.timetables['2004-fall', 'simple'] = new_tt
        tt = self.person.timetables['2004-fall', 'simple']
        self.assert_(new_act in tt['Day 1']['A'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestTimetableResourceSynchronizer))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
