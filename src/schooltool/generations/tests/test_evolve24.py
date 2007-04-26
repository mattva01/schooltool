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
Unit tests for schooltool.generations.evolve24

$Id$
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
from schooltool.resource.interfaces import IResource


class ResourceStub(object):
    implements(IAttributeAnnotatable, IResource)

    def __init__(self, name, description):
        self.__name__ = name
        self.title = name
        self.description = description
        self.isLocation = False
        # initialize annotations
        IAnnotations(self)['foo'] = 'init'

    def __conform__(self, iface):
        from schooltool.relationship.interfaces import IRelationshipLinks
        if iface == IRelationshipLinks:
            return []

    def __repr__(self):
        return self.__name__


class AppStub(dict):
    implements(ISchoolToolApplication)

    def __init__(self):
        # Real app has a simple unordered container, but we do not
        # want to depend on dictionary internal order in our tests
        self['resources'] = OrderedContainer()
        for name in ['r1', 'r2', 'r3']:
            self['resources'][name] = ResourceStub(name, 'foo')


def doctest_evolve24():
    """Evolution to generation 24.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

        >>> r1 = app['resources']['r1']

    All the non location resources are ignored:

        >>> from schooltool.generations.evolve24 import evolve
        >>> evolve(context)

        >>> r1 is app['resources']['r1']
        True

    Lets convert it to a location:

        >>> r1.isLocation = True

    Make sure arbitrary annotations carry over too:

        >>> from zope.annotation.interfaces import IAnnotations
        >>> from zope.annotation.attribute import AttributeAnnotations
        >>> class SomeAnnotation(object):
        ...     __parent__ = r1
        >>> annotation = SomeAnnotation()
        >>> IAnnotations(r1)['test'] = annotation

    Now evolve:

        >>> evolve(context)

    The resource was converted to a location object:

        >>> l1 = app['resources']['r1']
        >>> l1
        <schooltool.resource.resource.Location object at ...>

    With title and description set:

        >>> l1.title
        'r1'
        >>> l1.description
        'foo'

    And annotations fixed:

        >>> IAnnotations(l1)['test'] is annotation
        True

        >>> IAnnotations(l1)['test'].__parent__ is l1
        True

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
