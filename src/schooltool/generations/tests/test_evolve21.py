#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve21

$Id$
"""

import unittest

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.testing import setup
from zope.interface import implements
from zope.location.interfaces import ILocation
from zope.testing import doctest

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(dict):
    implements(ISchoolToolApplication, ILocation)
    __parent__ = None
    __name__ = None

    def __init__(self):
        self['sections'] = {}


class SectionStub(object):
    implements(IAttributeAnnotatable)

    def __init__(self, title):
        self.title = title

    def __repr__(self):
        return '<Section %s>' % self.title

    def __cmp__(self, other):
        if self.title == other.title:
            return 0
        return self.title < other.title and -1 or 1


def doctest_evolve():
    r"""Doctest for evolution to generation 21.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()

      >>> setup.placelessSetUp()
      >>> setup.setUpAnnotations()

      >>> event_list = []

      >>> from zope.event import subscribers
      >>> subscribers.append(event_list.append)

   If there are no timetables - nothing is done:

      >>> from schooltool.generations.evolve21 import evolve
      >>> evolve(context)
      >>> event_list
      []

   When we add some section without timetables - nothing happens too:

      >>> tt_key = 'schooltool.timetable.timetables'
      >>> from zope.annotation.interfaces import IAnnotations
      >>> s1 = app['sections']['section1'] = SectionStub("Section 1")
      >>> tts1 = IAnnotations(s1)[tt_key] = {}
      >>> s2 = app['sections']['section2'] = SectionStub("Section 2")
      >>> tts2 = IAnnotations(s2)[tt_key] = {}

      >>> evolve(context)
      >>> event_list
      []

   Let's add some timetables now:

      >>> tts1['term1.schema1'] = "Timetable 1"
      >>> tts2['term1.schema1'] = "Timetable 2"
      >>> tts2['term2.schema1'] = "Timetable 3"

   Events for every timetable are sent:

      >>> evolve(context)
      >>> sorted([(ev.object, ev.key, ev.old_timetable, ev.new_timetable)
      ...         for ev in event_list])
      [(<Section Section 1>, 'term1.schema1', None, 'Timetable 1'),
       (<Section Section 2>, 'term1.schema1', None, 'Timetable 2'),
       (<Section Section 2>, 'term2.schema1', None, 'Timetable 3')]

   Clean up subscribers:

      >>> subscribers = subscribers[:1]
      >>> setup.placefulTearDown()

    """

def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE
                                |doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
