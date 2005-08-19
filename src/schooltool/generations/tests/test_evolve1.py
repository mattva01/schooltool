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
Unit tests for schooltool.generations.evolve1

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app import zapi
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.app.publication.zopepublication import ZopePublication
from BTrees.OOBTree import OOBTree

def doctest_evolve1():
    """Evolution to generation 1.

    The first change in this evolution was the introduction of
    exceptionDays and exceptionDayIds attributes on the
    ITimetableModel implementations.  Their factories are registered
    as global utilities, and their instances are saved as a model
    attribute on ITimetableSchemas and, consequently, on timetables.

    Let's create some mock objects that demonstrates the current
    situation:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from schooltool.timetable.interfaces import ITimetableModel
        >>> class MockSchoolTool(dict):
        ...     implements(ISchoolToolApplication)

        >>> class MockTimetable:
        ...     model = None

        >>> class MockTimetableModel:
        ...     implements(ITimetableModel)

        >>> class MockPerson:
        ...     timetables = {}

    Let's say we have a schooltool object with two timetable schemas:

        >>> app = MockSchoolTool()
        >>> app['ttschemas'] = {}
        >>> app['persons'] = OOBTree()
        >>> app['groups'] = {}
        >>> app['resources'] = {}
        >>> app['ttschemas']["weekly"] = MockTimetable()
        >>> app['ttschemas']["sequential"] = MockTimetable()
        >>> app['ttschemas']["weekly"].model = MockTimetableModel()
        >>> app['ttschemas']["sequential"].model = MockTimetableModel()
        >>> model1 = app['ttschemas']["weekly"].model
        >>> model2 = app['ttschemas']["sequential"].model

    Also, there are some timetables utilizing these schemas:

        >>> app['persons']['albertas'] = MockPerson()
        >>> tts = app['persons']['albertas'].timetables
        >>> tts['2005.sequential'] = MockTimetable()
        >>> tts['2005.sequential'].model = model2

        >>> app['groups']['haxors'] = MockPerson()
        >>> tts = app['groups']['haxors'].timetables
        >>> tts['2005.weekly'] = MockTimetable()
        >>> tts['2005.weekly'].model = MockTimetableModel()
        >>> model4 = tts['2005.weekly'].model
        >>> model4.exceptionDayIds = {'foo': 'bar'}
        >>> model4.exceptionDays = {'do not': 'touch'}

    Also, strangely, there are timetables that use other schemas/models:

        >>> app['resources']['beamer'] = MockPerson()
        >>> tts = app['resources']['beamer'].timetables
        >>> tts['2005.bizarre'] = MockTimetable()
        >>> tts['2005.bizarre'].model = MockTimetableModel()
        >>> model3 = tts['2005.bizarre'].model

    Now, let's feed this app to the evolve script:

        >>> class MockContext:
        ...     pass
        >>> class MockConnection:
        ...     _root = {}
        ...     def root(self):
        ...         return self._root

        >>> context = MockContext()
        >>> context.connection = conn = MockConnection()
        >>> conn._root[ZopePublication.root_name] = {'app': app}

    Let's run the evolve script on this whole thing:

        >>> from schooltool.generations.evolve1 import evolve
        >>> evolve(context)

    Now all models we created must have exceptionDays and
    exceptionDayIds attributes, which should be empty PersistentDicts.

        >>> model1.exceptionDayIds
        <persistent.dict.PersistentDict ...>
        >>> model2.exceptionDayIds
        <persistent.dict.PersistentDict ...>
        >>> model3.exceptionDayIds
        <persistent.dict.PersistentDict ...>
        >>> model1.exceptionDays
        <persistent.dict.PersistentDict ...>
        >>> model2.exceptionDays
        <persistent.dict.PersistentDict ...>
        >>> model3.exceptionDays
        <persistent.dict.PersistentDict ...>

        >>> list(model1.exceptionDayIds)
        []
        >>> list(model2.exceptionDayIds)
        []
        >>> list(model3.exceptionDayIds)
        []
        >>> list(model1.exceptionDays)
        []
        >>> list(model2.exceptionDays)
        []
        >>> list(model3.exceptionDays)
        []

    Models that already had those attributes should not have been modified:

        >>> model4.exceptionDays
        {'do not': 'touch'}
        >>> model4.exceptionDayIds
        {'foo': 'bar'}

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
