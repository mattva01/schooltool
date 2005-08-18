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
Unit tests for schooltool.relationship

$Id$
"""

import unittest

from zope.testing import doctest


def doctest_relate():
    """Tests for relate

    getRelatedObjects relies on adapters to IRelationshipLinks.  For the
    purposes of this test it is simpler to just implement IRelationshipLinks
    directly in the object

        >>> from zope.interface import implements
        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> from schooltool.relationship.relationship import Link

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

        >>> from schooltool.relationship.relationship import relate
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
        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> from schooltool.relationship.relationship import Link

        >>> class Relatable:
        ...     implements(IRelationshipLinks)
        ...     def __iter__(self):
        ...         return iter([
        ...             Link('role_of_b', 'a', 'role_of_a', 'rel_type_a'),
        ...             Link('role_of_a', 'b', 'role_of_b', 'rel_type_b')])

        >>> obj = Relatable()

    Now we can test getRelatedObjects

        >>> from schooltool.relationship.relationship import getRelatedObjects
        >>> getRelatedObjects(obj, 'role_of_a')
        ['a']
        >>> getRelatedObjects(obj, 'role_of_b')
        ['b']
        >>> getRelatedObjects(obj, 'role_of_c')
        []

    """


def doctest_RelationshipSchema():
    """Tests for RelationshipSchema

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> setUp()

    The constructor takes exactly two keyword arguments

        >>> from schooltool.relationship import RelationshipSchema
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

        >>> from schooltool.relationship.tests import SomeObject
        >>> a, b = map(SomeObject, ['a', 'b'])
        >>> Management(manager=a, report=b)

    You will see that a is b's manager, and b is a's report:

        >>> from schooltool.relationship import getRelatedObjects
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

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> setUp()

    Let us catch all events and remember them

        >>> events = []
        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> zope.event.subscribers.append(events.append)

    Nothing happens if the object has no relationships.

        >>> from schooltool.relationship.tests import SomeObject
        >>> a = SomeObject('a')
        >>> from schooltool.relationship import unrelateAll
        >>> unrelateAll(a)
        >>> events
        []

    Suppose that the object has a number of relationships

        >>> from schooltool.relationship import relate
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

        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> list(IRelationshipLinks(a))
        []

    Relationships are broken properly, from both ends

        >>> from schooltool.relationship import getRelatedObjects
        >>> getRelatedObjects(b, 'example:Foo')
        []

    Also, we got a bunch of events

        >>> from sets import Set
        >>> from schooltool.relationship.interfaces \
        ...         import IBeforeRemovingRelationshipEvent
        >>> from schooltool.relationship.interfaces \
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


def test_suite():
    return unittest.TestSuite([
                doctest.DocFileSuite('../README.txt'),
                doctest.DocTestSuite('schooltool.relationship.relationship'),
                doctest.DocTestSuite(),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
