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
Unit tests for schoolbell.relationship

$Id$
"""

import unittest

from zope.testing import doctest
from zope.app.tests import setup
from zope.interface import implements
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container.contained import Contained


class SomeObject(object):
    """A simple annotatable object for tests."""

    implements(IAttributeAnnotatable)

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name


class SomeContained(SomeObject, Contained):
    """A simple annotatable contained object for tests."""


def setUp():
    """Set up for schoolbell.relationship doctests.

    Calls Zope's placelessSetUp, sets up annotations and relationships.
    """
    setup.placelessSetUp()
    setup.setUpAnnotations()
    setUpRelationships()


def tearDown():
    """Tear down for schoolbell.relationshp doctests."""
    setup.placelessTearDown()


def setUpRelationships():
    """Set up the adapter from IAnnotatable to IRelationshipLinks.

    This function is created for use in unit tests.  You should call
    zope.app.tests.setup.placelessSetUp before calling this function
    (and don't forget to call zope.app.tests.setup.placelessTearDown after
    you're done).  You should also call zope.app.tests.setup.setUpAnnotations
    to get a complete test fixture.
    """
    from zope.app.tests import ztapi
    from zope.app.annotation.interfaces import IAnnotatable
    from schoolbell.relationship.interfaces import IRelationshipLinks
    from schoolbell.relationship.annotatable import getRelationshipLinks
    ztapi.provideAdapter(IAnnotatable, IRelationshipLinks,
                         getRelationshipLinks)


def doctest_URIObject():
    """Tests for URIObject.

    URIObject's constructor takes three arguments: URI, name and description

        >>> from schoolbell.relationship.uri import URIObject
        >>> uri = URIObject('http://example.com', 'Example', 'An example.')
        >>> uri
        <URIObject Example>
        >>> uri.uri
        'http://example.com'
        >>> uri.name
        'Example'
        >>> uri.description
        'An example.'

    The attributes of an URIObject match those defined by IURIObject

        >>> from zope.interface.verify import verifyObject
        >>> from schoolbell.relationship.uri import IURIObject
        >>> verifyObject(IURIObject, uri)
        True

    Description is optional

        >>> uri = URIObject('http://example.com', 'Example')
        >>> uri.description
        ''

    Name is also optional

        >>> uri = URIObject('http://example.com')
        >>> uri.name

    XXX Why does description default to '', while name defaults to None?

    URIs must be syntactically valid

        >>> URIObject('not a URI')
        Traceback (most recent call last):
          ...
        ValueError: This does not look like a URI: 'not a URI'

    URIObjects are comparable.  Two URIObjects are equal if, and only if,
    their 'uri' attributes are equal.

        >>> uri2 = URIObject('http://example.com', 'Exampleur')
        >>> uri3 = URIObject('http://example.org', 'Exampleur')
        >>> uri2 == uri
        True
        >>> uri2 == uri3
        False
        >>> uri2 != uri
        False
        >>> uri2 != uri3
        True
        >>> uri == 'example:Just a string'
        False
        >>> uri != 'example:Just a string'
        True

    By the way, there are separate tests for == and != because in Python
    __eq__ and __ne__ are two different methods.

    What should uri == 'http://example.com' return?  I have decided that
    it should return False, because applications may rely on roles having
    `name` and `description` attributes, after they check the relationship
    type.

        >>> uri == 'http://example.com'
        False
        >>> uri != 'http://example.com'
        True

    URIObjects are hashable.  Equal objects must hash to the same value

        >>> hash(uri) == hash(uri2)
        True

    URIObjects are immutable

        >>> uri.uri = 'http://makemoneyfast.example.net'
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

        >>> uri.name = 'Friendship'
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

        >>> uri.description = 'Dunno'
        Traceback (most recent call last):
          ...
        AttributeError: can't set attribute

    """


def doctest_getRelationshipLinks():
    r"""Test for schoolbell.relationship.annotatable.getRelationshipLinks.

    We need to set up Zope 3 annotations

        >>> from zope.app.tests import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()

    We need to have an annotatable object

        >>> from zope.interface import implements
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> class SomeAnnotatable(object):
        ...     implements(IAttributeAnnotatable)

        >>> obj = SomeAnnotatable()

    Now we can check that a new LinkSet is created automatically

        >>> from schoolbell.relationship.annotatable \
        ...         import getRelationshipLinks
        >>> linkset = getRelationshipLinks(obj)

        >>> from schoolbell.relationship.interfaces import IRelationshipLinks
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IRelationshipLinks, linkset)
        True

    If you do it more than once, you will get the same link set

        >>> linkset is getRelationshipLinks(obj)
        True

    """


def doctest_relate():
    """Tests for relate

    getRelatedObjects relies on adapters to IRelationshipLinks.  For the
    purposes of this test it is simpler to just implement IRelationshipLinks
    directly in the object

        >>> from zope.interface import implements
        >>> from schoolbell.relationship.interfaces import IRelationshipLinks
        >>> from schoolbell.relationship.relationship import Link

        >>> class Relatable:
        ...     implements(IRelationshipLinks)
        ...     def __init__(self, name):
        ...         self._name = name
        ...     def __repr__(self):
        ...         return self._name
        ...     def __iter__(self):
        ...         return iter([])
        ...     def add(self, link):
        ...         print 'Linking %s with %s (the %s in %s)' % (self,
        ...                 link.target, link.role, link.rel_type)

        >>> fred = Relatable('Fred')
        >>> wilma = Relatable('Wilma')

    Now we can test relate

        >>> from schoolbell.relationship.relationship import relate
        >>> relate('marriage', (fred, 'husband'), (wilma, 'wife'))
        Linking Fred with Wilma (the wife in marriage)
        Linking Wilma with Fred (the husband in marriage)

    """


def doctest_getRelatedObjects():
    """Tests for getRelatedObjects

    getRelatedObjects relies on adapters to IRelationshipLinks.  For the
    purposes of this test it is simpler to just implement IRelationshipLinks
    directly in the object

        >>> from zope.interface import implements
        >>> from schoolbell.relationship.interfaces import IRelationshipLinks
        >>> from schoolbell.relationship.relationship import Link

        >>> class Relatable:
        ...     implements(IRelationshipLinks)
        ...     def __iter__(self):
        ...         return iter([
        ...             Link('role_of_b', 'a', 'role_of_a', 'rel_type_a'),
        ...             Link('role_of_a', 'b', 'role_of_b', 'rel_type_b')])

        >>> obj = Relatable()

    Now we can test getRelatedObjects

        >>> from schoolbell.relationship.relationship import getRelatedObjects
        >>> getRelatedObjects(obj, 'role_of_a')
        ['a']
        >>> getRelatedObjects(obj, 'role_of_b')
        ['b']
        >>> getRelatedObjects(obj, 'role_of_c')
        []

    """


def doctest_RelationshipSchema():
    """Tests for RelationshipSchema

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

    The constructor takes exactly two keyword arguments

        >>> from schoolbell.relationship import RelationshipSchema
        >>> RelationshipSchema('example:Mgmt', manager='example:Mgr',
        ...                    report='example:Rpt', supervisor='example:Spv')
        Traceback (most recent call last):
          ...
        TypeError: A relationship must have exactly two ends.
        >>> RelationshipSchema('example:Mgmt', manager='example:Mgr')
        Traceback (most recent call last):
          ...
        TypeError: A relationship must have exactly two ends.

    This works:

        >>> Management = RelationshipSchema('example:Mgmt',
        ...                                 manager='example:Mgr',
        ...                                 report='example:Rpt')

    You can call relationship schemas

        >>> a, b = map(SomeObject, ['a', 'b'])
        >>> Management(manager=a, report=b)

    You will see that a is b's manager, and b is a's report:

        >>> from schoolbell.relationship import getRelatedObjects
        >>> getRelatedObjects(b, 'example:Mgr')
        [a]
        >>> getRelatedObjects(a, 'example:Rpt')
        [b]

    Order of arguments does not matter

        >>> c, d = map(SomeObject, ['c', 'd'])
        >>> Management(report=c, manager=d)
        >>> getRelatedObjects(c, 'example:Mgr')
        [d]
        >>> getRelatedObjects(d, 'example:Rpt')
        [c]

    You must give correct arguments, though

        >>> Management(report=c, friend=d)
        Traceback (most recent call last):
          ...
        TypeError: Missing a 'manager' keyword argument.

        >>> Management(manager=c, friend=d)
        Traceback (most recent call last):
          ...
        TypeError: Missing a 'report' keyword argument.

    You should not give extra arguments either

        >>> Management(report=c, manager=b, friend=d)
        Traceback (most recent call last):
          ...
        TypeError: Too many keyword arguments.

    """


def doctest_unrelateAll():
    r"""Tests for unrelateAll.

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

    Let us catch all events and remember them

        >>> events = []
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(events.append)

    Nothing happens if the object has no relationships.

        >>> a = SomeObject('a')
        >>> from schoolbell.relationship import unrelateAll
        >>> unrelateAll(a)
        >>> events
        []

    Suppose that the object has a number of relationships

        >>> from schoolbell.relationship import relate
        >>> b, c, d = map(SomeObject, ['b', 'c', 'd'])
        >>> relationships = [
        ...       ('example:SomeRelationship', (a, 'example:Foo'),
        ...                                    (b, 'example:Bar')),
        ...       ('example:SomeRelationship', (a, 'example:Foo'),
        ...                                    (c, 'example:Bar')),
        ...       ('example:OtherRelationship', (a, 'example:Symmetric'),
        ...                                     (d, 'example:Symmetric')),
        ...       ('example:Loop', (a, 'example:OneEnd'),
        ...                        (a, 'example:OtherEnd')),
        ...       ('example:Loop', (a, 'example:BothEnds'),
        ...                        (a, 'example:BothEnds')),
        ... ]
        >>> for args in relationships:
        ...     relate(*args)

    We are not interested in relationship events up to this point

        >>> del events[:]

    We call `unrelateAll` and it suddenly has no relationships

        >>> unrelateAll(a)

        >>> from schoolbell.relationship.interfaces import IRelationshipLinks
        >>> list(IRelationshipLinks(a))
        []

    Relationships are broken properly, from both ends

        >>> from schoolbell.relationship import getRelatedObjects
        >>> getRelatedObjects(b, 'example:Foo')
        []

    Also, we got a bunch of events

        >>> from sets import Set
        >>> from schoolbell.relationship.interfaces \
        ...         import IBeforeRemovingRelationshipEvent
        >>> from schoolbell.relationship.interfaces \
        ...         import IRelationshipRemovedEvent
        >>> before_removal_events = Set([
        ...         (e.rel_type, (e.participant1, e.role1),
        ...                      (e.participant2, e.role2))
        ...         for e in events
        ...         if IBeforeRemovingRelationshipEvent.providedBy(e)])
        >>> before_removal_events == Set(relationships)
        True

        >>> removal_events = Set([(e.rel_type, (e.participant1, e.role1),
        ...                        (e.participant2, e.role2))
        ...                       for e in events
        ...                       if IRelationshipRemovedEvent.providedBy(e)])
        >>> removal_events == Set(relationships)
        True

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_delete_breaks_relationships():
    """When you delete an object, all of its relationships should be removed

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schoolbell.relationship.objectevents import unrelateOnDeletion
        >>> zope.event.subscribers.append(unrelateOnDeletion)

    Suppose we have two related objects

        >>> from schoolbell.relationship.tests import SomeObject
        >>> apple = SomeObject('apple')
        >>> orange = SomeObject('orange')

        >>> from schoolbell.relationship import getRelatedObjects, relate
        >>> relate('example:Relationship',
        ...             (apple, 'example:One'),
        ...             (orange, 'example:Two'))
        >>> getRelatedObjects(apple, 'example:Two')
        [orange]

    We put those objects to a Zope 3 container.

        >>> from zope.app.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> container['apple'] = apple
        >>> container['orange'] = orange

    When we delete an object, all of its relationships should disappear

        >>> del container['orange']
        >>> getRelatedObjects(apple, 'example:Two')
        []

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_copy_breaks_relationships():
   """When you copy an object, all of its relationships should be removed

   (An alternative solution would be to clone the relationships, but I'm
   wary of that path.  What happens if you copy and paste objects between
   different application instances?)

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schoolbell.relationship.objectevents import unrelateOnCopy
        >>> zope.event.subscribers.append(unrelateOnCopy)

    Suppose we have two related objects.  We must have objects that are
    IContained, otherwise ObjectCopier will happily duplicate all related
    objects as well as relationship links.

        >>> from schoolbell.relationship.tests import SomeContained
        >>> apple = SomeContained('apple')
        >>> orange = SomeContained('orange')

        >>> from schoolbell.relationship import getRelatedObjects, relate
        >>> relate('example:Relationship',
        ...             (apple, 'example:One'),
        ...             (orange, 'example:Two'))
        >>> getRelatedObjects(apple, 'example:Two')
        [orange]

    We put those objects to a Zope 3 container.

        >>> from zope.app.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> container['apple'] = apple
        >>> container['orange'] = orange

    We copy one of the objects to another container.

        >>> from zope.app.copypastemove import ObjectCopier
        >>> another_container = BTreeContainer()
        >>> copier = ObjectCopier(container['orange'])
        >>> new_name = copier.copyTo(another_container)
        >>> copy_of_orange = another_container[new_name]

    When we copy an object, all of its relationships should disappear

        >>> from schoolbell.relationship.interfaces import IRelationshipLinks
        >>> list(IRelationshipLinks(copy_of_orange))
        []

    The old relationships should still work

        >>> getRelatedObjects(apple, 'example:Two')
        [orange]
        >>> getRelatedObjects(orange, 'example:One')
        [apple]

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocFileSuite('README.txt'),
                doctest.DocTestSuite('schoolbell.relationship.uri'),
                doctest.DocTestSuite('schoolbell.relationship.relationship'),
                doctest.DocTestSuite(),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
