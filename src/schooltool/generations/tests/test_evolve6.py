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
Unit tests for schooltool.generations.evolve6

$Id$
"""

import unittest

from zope.app.testing import setup
from zope.testing import doctest
from zope.app.container.btree import BTreeContainer

from schooltool.generations.tests import ContextStub
import schooltool.app # Dead chicken to avoid issue 390
from schooltool.person.person import Person
from schooltool.resource.resource import Resource
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.testing import setup as sbsetup
from schooltool.relationship.tests import setUpRelationships


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()
    sbsetup.setupCalendaring()
    setUpRelationships()


def tearDown(test):
    setup.placelessTearDown()


def doctest_evolve6_get_rid_of_dead_calendars():
    """Evolution to generation 6.

        >>> context = ContextStub()
        >>> app = {'persons': BTreeContainer()}
        >>> context.root_folder['app'] = app

    The problem happens like this: we have a Person in the application.

        >>> person = Person()
        >>> app['persons']['person'] = person

    There is another person, but it has been deleted

        >>> dead_person = Person()

    The first person has overlaid the dead person's calendar.

        >>> dead_persons_calendar = ISchoolToolCalendar(dead_person)
        >>> person.overlaid_calendars.add(dead_persons_calendar)

    (In real life, dead_person was alive when person overlaid his
    calendar, but then dead_person got removed.  The late person's
    calendar was supposed to be removed from all overlays, but that
    didn't happen because of a bug.)

    This evolution script is supposed to clean up such stale calendars
    from overlay lists.

        >>> from schooltool.generations.evolve6 import evolve
        >>> evolve(context)

    We can see that the stale calendar is gone now:

        >>> list(person.overlaid_calendars)
        []

    """


def doctest_evolve6_doesnt_do_too_much():
    """Evolution to generation 6.

        >>> context = ContextStub()

        >>> person = Person()
        >>> context.root_folder['person1'] = person
        >>> another_person = Person()
        >>> context.root_folder['person2'] = another_person

    The evolution script shouldn't remove valid calendar overlays

        >>> another_persons_calendar = ISchoolToolCalendar(another_person)
        >>> person.overlaid_calendars.add(another_persons_calendar)

    The evolution script shouldn't try to access nonexistent properties
    of other objects

        >>> context.root_folder['resource1'] = Resource()

    Let's see that it doesn't do either

        >>> from schooltool.generations.evolve6 import evolve
        >>> evolve(context)

        >>> len(person.overlaid_calendars)
        1

    """


def doctest_evolve6_removal_while_iteration():
    """Evolution to generation 6.

    The script needs to iterate over all related calendars and remove
    some of them.  Removal during iteration is always tricky.

        >>> context = ContextStub()
        >>> person = Person()
        >>> context.root_folder['person1'] = person

        >>> for n in range(20):
        ...     dead_person = Person()
        ...     dead_persons_calendar = ISchoolToolCalendar(dead_person)
        ...     person.overlaid_calendars.add(dead_persons_calendar)

        >>> from schooltool.generations.evolve6 import evolve
        >>> evolve(context)

    We can see that all the stale calendars are gone now:

        >>> list(person.overlaid_calendars)
        []

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                    |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
