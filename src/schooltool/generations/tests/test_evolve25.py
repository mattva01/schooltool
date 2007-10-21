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

$Id: test_evolve21.py 6527 2006-12-28 12:25:35Z ignas $
"""

import unittest

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.testing import setup
from zope.interface import implements
from zope.location.interfaces import ILocation
from zope.testing import doctest

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.gradebook.activity import Activities, Activity, Worksheet

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


def doctest_evolve():
    r"""Doctest for evolution to generation 25.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()
      >>> setup.placelessSetUp()
      >>> setup.setUpAnnotations()

   We create a section with some activies attached to it.

      >>> from zope.annotation.interfaces import IAnnotations
      >>> s1 = app['sections']['section1'] = SectionStub("Section 1")
      >>> ann = IAnnotations(s1)
      >>> activities = Activities('1')
      >>> ann['schooltool.gradebook.activities'] = activities
      >>> activities['1'] = Activity('Homework1', '', '')
      >>> activities['2'] = Activity('Final', '', '')

   This is the old way activites were stored.
   
      >>> list(activities.items())
      [('1', <Activity 'Homework1'>), ('2', <Activity 'Final'>)]
      
   Now let's evolve and note that the activites hold a new worksheet
   and that the worksheet holds the actual activity objects.
   
      >>> from schooltool.generations.evolve25 import evolve
      >>> evolve(context)
      >>> list(activities.items())
      [('Worksheet', Worksheet('Worksheet1'))]
      >>> worksheet = activities['Worksheet']
      >>> list(worksheet.items())
      [('1', <Activity 'Homework1'>), ('2', <Activity 'Final'>)]

   Clean up test.

      >>> setup.placefulTearDown()
      
    """

def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE
                                |doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
