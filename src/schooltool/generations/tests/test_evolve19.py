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
Unit tests for schooltool.generations.evolve19

$Id$
"""

import unittest

from zope.app.testing import setup
from zope.location.interfaces import ILocation
from zope.testing import doctest
from zope.interface import implements

from schooltool.app.interfaces import IHaveCalendar
from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(dict):
    implements(ISchoolToolApplication, ILocation)
    __parent__ = None
    __name__ = None


class HaveCalendarStub(object):
    implements(IHaveCalendar)

    def __init__(self):
        self.__annotations__ = {}
        self.__annotations__['schooltool.app.calendar.Calendar'] = []

    def addEvent(self, event):
        self.__annotations__['schooltool.app.calendar.Calendar'].append(event)


class EventStub(object):
    def __init__(self, uid):
        self.unique_id = uid
        self.__name__ = uid


def doctest_evolve():
    r"""Doctest for evolution to generation 19.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()
      >>> calendar1 = app['c1'] = HaveCalendarStub()
      >>> calendar2 = app['c2'] = HaveCalendarStub()
      >>> ev1 = EventStub('lala')
      >>> ev2 = EventStub('bobo')
      >>> ev3 = EventStub('unique/id')
      >>> ev4 = EventStub('@very/very/very/long/and/really_really_really/unique/id')
      >>> calendar1.addEvent(ev1)
      >>> calendar2.addEvent(ev2)
      >>> calendar2.addEvent(ev3)
      >>> calendar2.addEvent(ev4)

      >>> from schooltool.generations.evolve19 import evolve
      >>> evolve(context)

      >>> ev1.__name__
      'bGFsYQ=='
      >>> ev2.__name__
      'Ym9ibw=='
      >>> ev3.__name__
      'dW5pcXVlL2lk'
      >>> ev4.__name__
      'QHZlcnkvdmVyeS92ZXJ5L2xvbmcvYW5kL3JlYWxseV9yZWFsbHlfcmVhbGx5L3VuaXF1ZS9pZA=='

    """

def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()

def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
