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
Unit tests for schooltool.generations.evolve13

$Id: test_evolve12.py 5946 2006-04-18 15:47:33Z ignas $
"""

import unittest

from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements
from zope.component import adapts, provideAdapter
from zope.app.container.ordered import OrderedContainer
from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication

class StudentStub(object):
    implements(IAttributeAnnotatable)
    
    def __init__(self, name):
        self.__name__ = name
        self.username = name
        self.title = name
        self.photo = None
        self._hashed_password = None
        self.groups = []
        self.overlaid_calendars = None
        # initialize annotations
        IAnnotations(self)['foo'] = 'init'
        
    def __repr__(self):
        return self.__name__

class AppStub(dict):
    implements(ISchoolToolApplication)

    def __init__(self):
        # Real app has a simple unordered container, but we do not
        # want to depend on dictionary internal order in our tests
        self['persons'] = OrderedContainer()
        for name in ['s1', 's2', 's3']:
            self['persons'][name] = StudentStub(name)

def doctest_evolve14():
    """Evolution to generation 14.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

        >>> s1 = app['persons']['s1']
        >>> hasattr(s1, 'nameinfo')
        False

       Make sure arbitrary annotations carry over too:

        >>> from zope.annotation.interfaces import IAnnotations
        >>> from zope.annotation.attribute import AttributeAnnotations
        >>> IAnnotations(s1)['test'] = 'Bar'

       Now evolve:
       
        >>> from schooltool.generations.evolve14 import evolve
        >>> evolve(context)
        >>> s1 = app['persons']['s1']
        >>> hasattr(s1, 'nameinfo')
        True

        >>> s1.username == 's1'
        True
        >>> IAnnotations(s1)['test']
        'Bar'
    """

def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
