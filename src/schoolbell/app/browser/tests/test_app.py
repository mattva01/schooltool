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
Tests for schoolbell views.

$Id$
"""

import unittest
from zope.testing import doctest
from zope.app.tests import setup
from zope.interface import implements, directlyProvides
from zope.app.traversing.interfaces import IContainmentRoot
from zope.publisher.browser import TestRequest


def test_personContainerView():
    r"""Test for PersonContainerView

    We will need to set up the environment for the test:

        >>> setup.placelessSetUp()

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> schoolBellApplication = SchoolBellApplication()
        >>> directlyProvides(schoolBellApplication, IContainmentRoot)

    Let's create a new person:

        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> person.__name__ = "Jonas"
        >>> person.title = "Jonas Petraitis"

    Lets add him to the container

        >>> person.__parent__ = schoolBellApplication
        >>> schoolBellApplication['persons'][person.__name__] = person

    Lets add another person to the container

        >>> person = Person()
        >>> person.__name__ = "Petras"
        >>> person.title = "Abdul Petras"
        >>> person.__parent__ = schoolBellApplication
        >>> schoolBellApplication['persons'][person.__name__] = person

    Lets create a view

        >>> from schoolbell.app.browser.app import PersonContainerView
        >>> view = PersonContainerView(schoolBellApplication['persons'],
        ...                            TestRequest())

    Lets get a sorted by title object list

        >>> sortedObjects = view.sortedObjects()

        >>> sortedObjects[0].title
        'Abdul Petras'

        >>> sortedObjects[1].title
        'Jonas Petraitis'

        >>> view.index_title
        u'Person index'

        >>> view.add_title
        u'Add a new person'

        >>> view.add_url
        'addSchoolBellPerson.html'

        >>> setup.placelessTearDown()
    """


def test_groupContainerView():
    r"""Test for GroupContainerView

    We will need to set up the environment for the test:

        >>> setup.placelessSetUp()

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> schoolBellApplication = SchoolBellApplication()
        >>> directlyProvides(schoolBellApplication, IContainmentRoot)

    Let's create a new group:

        >>> from schoolbell.app.app import Group
        >>> group = Group()
        >>> group.__name__ = "Group B"
        >>> group.title = "Group B"

    Lets add it to the container

        >>> group.__parent__ = schoolBellApplication
        >>> schoolBellApplication['groups'][group.__name__] = group

    Lets add another group to the container

        >>> group = Group()
        >>> group.__name__ = "Group A"
        >>> group.title = "Group A"
        >>> group.__parent__ = schoolBellApplication
        >>> schoolBellApplication['groups'][group.__name__] = group

    Lets create a view

        >>> from schoolbell.app.browser.app import GroupContainerView
        >>> view = GroupContainerView(schoolBellApplication['groups'],
        ...                            TestRequest())

    Lets get a sorted by title object list

        >>> sortedObjects = view.sortedObjects()

        >>> sortedObjects[0].title
        'Group A'

        >>> sortedObjects[1].title
        'Group B'

        >>> view.index_title
        u'Group index'

        >>> view.add_title
        u'Add a new group'

        >>> view.add_url
        'addSchoolBellGroup.html'

        >>> setup.placelessTearDown()
    """


def test_resourceContainerView():
    r"""Test for ResourceContainerView

    We will need to set up the environment for the test:

        >>> setup.placelessSetUp()

        >>> from schoolbell.app.app import SchoolBellApplication
        >>> schoolBellApplication = SchoolBellApplication()
        >>> directlyProvides(schoolBellApplication, IContainmentRoot)

    Let's create a new resource:

        >>> from schoolbell.app.app import Resource
        >>> resource = Resource()
        >>> resource.__name__ = "Resource B"
        >>> resource.title = "Resource B"

    Lets add it to the container

        >>> resource.__parent__ = schoolBellApplication
        >>> schoolBellApplication['resources'][resource.__name__] = resource

    Lets add another resource to the container

        >>> resource = Resource()
        >>> resource.__name__ = "Resource A"
        >>> resource.title = "Resource A"
        >>> resource.__parent__ = schoolBellApplication
        >>> schoolBellApplication['resources'][resource.__name__] = resource

    Lets create a view

        >>> from schoolbell.app.browser.app import ResourceContainerView
        >>> view = ResourceContainerView(schoolBellApplication['resources'],
        ...                            TestRequest())

    Lets get a sorted by title object list

        >>> sortedObjects = view.sortedObjects()

        >>> sortedObjects[0].title
        'Resource A'

        >>> sortedObjects[1].title
        'Resource B'

        >>> view.index_title
        u'Resource index'

        >>> view.add_title
        u'Add a new resource'

        >>> view.add_url
        'addSchoolBellResource.html'
    """


def test_personView():
    r"""Test for PersonView

    Let's create a new person:

        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> person.__name__ = "Jonas"
        >>> person.title = "Jonas Petraitis"

    Let's create a person view
        >>> request = TestRequest()
        >>> request.setPrincipal(person)
        >>> from schoolbell.app.browser.app import PersonView
        >>> view = PersonView(person, request)

    User can change his password
        >>> view.canChangePassword()
        True

    View his callendars
        >>> view.canViewCalendar()
        True

    Choose his callendars
        >>> view.canViewCalendar()
        True
    """


def test_personPhotoView():
    r"""Test for PersonPhotoView

    Let's create a new person:

        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> person.__name__ = "Jonas"
        >>> person.title = "Jonas Petraitis"
        >>> person.photo = "I am a photo!"

    Let's create a person photo view
        >>> request = TestRequest()
        >>> from schoolbell.app.browser.app import PersonPhotoView
        >>> view = PersonPhotoView(person, request)

    We should see the photo
        >>> view.__call__()
        'I am a photo!'

    The photo should be jpeg
        >>> request.response.getHeader("Content-Type")
        'image/jpeg'

    But if a person has no photo
        >>> person.photo = None

    We should get an exception
        >>> view.__call__()  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotFound: Object: <...Person object at ...>, name: u'photo'

        >>> setup.placelessTearDown()
    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
