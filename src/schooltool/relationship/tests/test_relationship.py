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
"""

import unittest

from zope.testing import doctest
from schooltool.relationship.tests import URIStub


def doctest_relate():
    """Tests for relate

    getRelatedObjects relies on adapters to IRelationshipLinks.  For the
    purposes of this test it is simpler to just implement IRelationshipLinks
    directly in the object

        >>> from zope.interface import implements
        >>> from schooltool.relationship.interfaces import IRelationshipLinks

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
        ...                 link.target, link.role.uri, link.rel_type)

        >>> fred = Relatable('Fred')
        >>> wilma = Relatable('Wilma')

    Now we can test relate

        >>> from schooltool.relationship.relationship import relate

        >>> husband = URIStub('husband')
        >>> wife = URIStub('wife')

        >>> relate('marriage', (fred, husband), (wilma, wife))
        Linking Fred with Wilma (the wife in marriage)
        Linking Wilma with Fred (the husband in marriage)

    """


def doctest_LinkSet_getTargetsByRole():
    """Tests for getTargetsByRole

        >>> from schooltool.relationship.relationship import LinkSet, Link

        >>> obj = LinkSet()

        >>> role_a = URIStub('role_of_a')
        >>> role_b = URIStub('role_of_b')

        >>> obj.add(Link(role_b, 'a', role_a, 'rel_type_a'))
        >>> obj.add(Link(role_a, 'b', role_b, 'rel_type_b'))

    Now we can test getTargetsByRole

        >>> obj.getTargetsByRole(role_a)
        ['a']
        >>> obj.getTargetsByRole(role_b)
        ['b']
        >>> obj.getTargetsByRole(URIStub('role_c'))
        []

    """


def doctest_RelationshipSchema():
    """Tests for RelationshipSchema

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> setUp()

    The constructor takes exactly two keyword arguments

        >>> from schooltool.relationship import RelationshipSchema
        >>> role_mgr = URIStub('example:Mgr')
        >>> role_rpt = URIStub('example:Rpt')
        >>> role_spv = URIStub('example:Spv')
        >>> RelationshipSchema('example:Mgmt', manager=role_mgr,
        ...                    report=role_rpt, supervisor=role_spv)
        Traceback (most recent call last):
          ...
        TypeError: A relationship must have exactly two ends.
        >>> RelationshipSchema('example:Mgmt', manager='example:Mgr')
        Traceback (most recent call last):
          ...
        TypeError: A relationship must have exactly two ends.

    This works:

        >>> Management = RelationshipSchema('example:Mgmt',
        ...                                 manager=role_mgr,
        ...                                 report=role_rpt)

    You can call relationship schemas

        >>> from schooltool.relationship.tests import SomeObject
        >>> a = SomeObject('a')
        >>> b = SomeObject('b')
        >>> Management(manager=a, report=b)

    You will see that a is b's manager, and b is a's report:

        >>> from schooltool.relationship import getRelatedObjects
        >>> getRelatedObjects(b, role_mgr)
        [a]
        >>> getRelatedObjects(a, role_rpt)
        [b]

    Order of arguments does not matter

        >>> c, d = map(SomeObject, ['c', 'd'])
        >>> Management(report=c, manager=d)
        >>> getRelatedObjects(c, role_mgr)
        [d]
        >>> getRelatedObjects(d, role_rpt)
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

    Cleanup

        >>> tearDown()

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
        >>> for rel_type, (a, rel_a), (b, rel_b) in relationships:
        ...     relate(rel_type, (a, URIStub(rel_a)), (b, URIStub(rel_b)))

    We are not interested in relationship events up to this point

        >>> del events[:]

    We call `unrelateAll` and it suddenly has no relationships

        >>> unrelateAll(a)

        >>> from schooltool.relationship.interfaces import IRelationshipLinks
        >>> list(IRelationshipLinks(a))
        []

    Relationships are broken properly, from both ends

        >>> from schooltool.relationship import getRelatedObjects
        >>> getRelatedObjects(b, URIStub('example:Foo'))
        []

    Also, we got a bunch of events

        >>> from schooltool.relationship.interfaces \
        ...         import IBeforeRemovingRelationshipEvent
        >>> from schooltool.relationship.interfaces \
        ...         import IRelationshipRemovedEvent
        >>> before_removal_events = set([
        ...         (e.rel_type, (e.participant1, e.role1.uri),
        ...                      (e.participant2, e.role2.uri))
        ...         for e in events
        ...         if IBeforeRemovingRelationshipEvent.providedBy(e)])
        >>> before_removal_events == set(relationships)
        True

        >>> removal_events = set([(e.rel_type,
        ...                        (e.participant1, e.role1.uri),
        ...                        (e.participant2, e.role2.uri))
        ...                       for e in events
        ...                       if IRelationshipRemovedEvent.providedBy(e)])
        >>> removal_events == set(relationships)
        True

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_BoundRelationshipProperty():
    """Tests for BoundRelationshipProperty.

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> setUp()

    Set up two types of membership.

        >>> role_student = URIStub('example:Student')
        >>> role_instructor = URIStub('example:Instructor')
        >>> role_course = URIStub('example:Course')

        >>> uri_attending = URIStub('example:Attending')
        >>> uri_instruction = URIStub('example:Instruction')

        >>> from schooltool.relationship import RelationshipSchema
        >>> Instruction = RelationshipSchema(uri_instruction,
        ...                                  instructor=role_instructor,
        ...                                  course=role_course)
        >>> Attending = RelationshipSchema(uri_attending,
        ...                                student=role_student,
        ...                                course=role_course)

    Create Course and Person classes.  We will use the RelationshipProperty
    that should bind to an instance as BoundRelationshipProperty.

        >>> from schooltool.relationship.tests import SomeObject
        >>> from schooltool.relationship.relationship import RelationshipProperty

        >>> class Course(SomeObject):
        ...     students = RelationshipProperty(
        ...         uri_attending, role_course, role_student)
        ...     instructors = RelationshipProperty(
        ...         uri_instruction, role_course, role_instructor)

        >>> class Person(SomeObject):
        ...     attends = RelationshipProperty(
        ...         uri_attending, role_student, role_course)
        ...     instructs = RelationshipProperty(
        ...         uri_instruction, role_instructor, role_course)

    Set up a course with several students.

        >>> course_a = Course('course A')

        >>> john, peter, cathy = students = [
        ...     Person(name) for name in ['John', 'Peter', 'Cathy']]
        >>> for student in students:
        ...     Attending(student=student, course=course_a)

    Set up a teacher that instructs the two courses.

        >>> teacher = Person('William')
        >>> course_b = Course('course B')
        >>> Instruction(instructor=teacher, course=course_a)
        >>> Instruction(instructor=teacher, course=course_b)

    We're done with preparations.

    Check that relationship properties were bound.

        >>> course_a.students
        <schooltool.relationship.relationship.BoundRelationshipProperty object ...>
        >>> teacher.instructs
        <schooltool.relationship.relationship.BoundRelationshipProperty object ...>

    They can be used to add and remove relationships, can be iterated to obtain
    related objects and have other useful methods.

        >>> bool(course_b.students)
        False

        >>> for student in students:
        ...     course_b.students.add(student)

        >>> len(course_b.students)
        3

        >>> course_b.students.remove(john)

        >>> len(course_b.students)
        2

        >>> bool(course_b.students)
        True

        >>> list(course_b.students)
        [Peter, Cathy]

    You can also obtain RelationshipInfo helpers for related objects.

        >>> course_a.instructors.relationships
        [<schooltool.relationship.relationship.RelationshipInfo object ...>]

        >>> rel_info = course_a.instructors.relationships[0]
        >>> rel_info.source
        course A
        >>> rel_info.target
        William

    Notice that 'source' in RelationshipInfo is the instace that
    BoundRelationshipProperty is bound to.  Let's look at the info for a class
    that William teaches.

        >>> list(teacher.instructs)
        [course A, course B]

        >>> rel_info = teacher.instructs.relationships[0]
        >>> rel_info.source
        William
        >>> rel_info.target
        course A

    Finally, let's check that BoundRelationshipProperty.relationships are
    filtered correctly.

        >>> [info.target for info in course_b.students.relationships]
        [Peter, Cathy]
        >>> [info.target for info in course_b.instructors.relationships]
        [William]

        >>> tearDown()

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    return unittest.TestSuite([
                doctest.DocFileSuite('../README.txt'),
                doctest.DocTestSuite('schooltool.relationship.relationship'),
                doctest.DocTestSuite(optionflags=optionflags),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
