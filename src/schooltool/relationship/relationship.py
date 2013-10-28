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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Implementation of relationships.

Relationships are represented as collections of links.  A link defines one
half of a relationship.  The storage of links on an object is determined by
an IRelationshipLinks adapter.  There is a default adapter registered for
all IAnnotatable objects that uses Zope 3 annotations.
"""
import datetime

from BTrees.OOBTree import OOBTree
from persistent import Persistent
from persistent.list import PersistentList
from persistent.dict import PersistentDict
from zope.container.contained import Contained
from zope.interface import implements
import zope.event

from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.interfaces import IRelationshipInfo
from schooltool.relationship.interfaces import IRelationshipLink
from schooltool.relationship.interfaces import IRelationshipProperty
from schooltool.relationship.interfaces import IBeforeRelationshipEvent
from schooltool.relationship.interfaces import IRelationshipAddedEvent
from schooltool.relationship.interfaces import IBeforeRemovingRelationshipEvent
from schooltool.relationship.interfaces import IRelationshipRemovedEvent
from schooltool.relationship.interfaces import DuplicateRelationship
from schooltool.relationship.interfaces import NoSuchRelationship
from schooltool.relationship.interfaces import IRelationshipSchema


def share_state(link_a, link_b):
    if (link_a.shared_state is not None and
        link_a.shared_state is link_b.shared_state):
        return
    if link_a.shared_state is not None:
        link_b.shared_state = link_a.shared_state
    elif link_b.shared_state is not None:
        link_a.shared_state = link_b.shared_state
    else:
        link_a.shared_state = link_b.shared_state = PersistentDict()


def relate(rel_type, (a, role_of_a), (b, role_of_b), extra_info=None):
    """Establish a relationship between objects `a` and `b`."""
    for link in IRelationshipLinks(a):
        if (link.target is b and link.role == role_of_b
            and link.rel_type == rel_type):
            raise DuplicateRelationship
    zope.event.notify(BeforeRelationshipEvent(rel_type,
                                              (a, role_of_a),
                                              (b, role_of_b),
                                              extra_info))
    link_a = Link(role_of_a, b, role_of_b, rel_type, extra_info)
    IRelationshipLinks(a).add(link_a)
    link_b = Link(role_of_b, a, role_of_a, rel_type, extra_info)
    IRelationshipLinks(b).add(link_b)
    share_state(link_a, link_b)
    zope.event.notify(RelationshipAddedEvent(rel_type,
                                             (a, role_of_a),
                                             (b, role_of_b),
                                             extra_info))


def unrelate(rel_type, (a, role_of_a), (b, role_of_b)):
    """Break a relationship between objects `a` and `b`."""
    links_of_a = IRelationshipLinks(a)
    links_of_b = IRelationshipLinks(b)
    try:
        link_a_to_b = links_of_a.find(role_of_a, b, role_of_b, rel_type)
    except ValueError:
        raise NoSuchRelationship
    extra_info = link_a_to_b.extra_info
    zope.event.notify(BeforeRemovingRelationshipEvent(rel_type,
                                                      (a, role_of_a),
                                                      (b, role_of_b),
                                                      extra_info))
    links_of_a.remove(link_a_to_b)
    # If links_of_b.find raises a ValueError, our data structures are out of
    # sync.
    link_b_to_a = links_of_b.find(role_of_b, a, role_of_a, rel_type)
    links_of_b.remove(link_b_to_a)
    zope.event.notify(RelationshipRemovedEvent(rel_type,
                                               (a, role_of_a),
                                               (b, role_of_b),
                                               extra_info))


def unrelateAll(obj):
    """Break all relationships of `obj`.

    Note that this operation is not atomic: if an event subscriber catches
    a BeforeRemovingRelationshipEvent and vetoes the operation, some
    relationships may have been removed, while others may still be there.
    """
    links_of_a = IRelationshipLinks(obj)
    relationships = [(link.rel_type, (obj, link.my_role),
                                     (link.target, link.role))
                     for link in links_of_a]
    for args in relationships:
        try:
            unrelate(*args)
        except NoSuchRelationship:
            pass # it was a loop, so we tried to delete it twice
    return


class RelationshipEvent(object):
    """Base class for relationship events.

        >>> event = RelationshipEvent('Membership',
        ...                           ('a', 'Member'), ('b', 'Group'),
        ...                           None)
        >>> event['Member']
        'a'
        >>> event['Group']
        'b'
        >>> event['Bogus']
        Traceback (most recent call last):
          ...
        KeyError: 'Bogus'

    """

    def __init__(self, rel_type, (a, role_of_a), (b, role_of_b), extra_info):
        self.rel_type = rel_type
        self.participant1 = a
        self.role1 = role_of_a
        self.participant2 = b
        self.role2 = role_of_b
        self.extra_info = extra_info

    def __getitem__(self, role):
        """Return the participant with a given role."""
        if role == self.role1:
            return self.participant1
        if role == self.role2:
            return self.participant2
        raise KeyError(role)

    def match(self, schema):
        if self.rel_type != schema.rel_type:
            return None
        schema_roles = tuple(schema.roles.values())
        if ((self.role1, self.role2) != schema_roles and
            (self.role2, self.role1) != schema_roles):
            return None
        return RelationshipMatch(self, schema)


class RelationshipMatch(object):

    def __init__(self, event, schema):
        self._event = event
        self._schema = schema
        self.extra_info = event.extra_info
        for name, role in schema.roles.items():
            if role == event.role1:
                setattr(self, name, event.participant1)
            elif role == event.role2:
                setattr(self, name, event.participant2)


class BeforeRelationshipEvent(RelationshipEvent):
    """A relationship is about to be established.

        >>> from zope.interface.verify import verifyObject
        >>> event = BeforeRelationshipEvent('example:Membership',
        ...                                 ('a', 'example:Member'),
        ...                                 ('letters', 'example:Group'),
        ...                                 None)
        >>> verifyObject(IBeforeRelationshipEvent, event)
        True

    """

    implements(IBeforeRelationshipEvent)


class RelationshipAddedEvent(RelationshipEvent):
    """A relationship has been established.

        >>> from zope.interface.verify import verifyObject
        >>> event = RelationshipAddedEvent('example:Membership',
        ...                                ('a', 'example:Member'),
        ...                                ('letters', 'example:Group'),
        ...                                None)
        >>> verifyObject(IRelationshipAddedEvent, event)
        True

    """

    implements(IRelationshipAddedEvent)


class BeforeRemovingRelationshipEvent(RelationshipEvent):
    """A relationship is about to be broken.

        >>> from zope.interface.verify import verifyObject
        >>> event = BeforeRemovingRelationshipEvent('example:Membership',
        ...                 ('a', 'example:Member'),
        ...                 ('letters', 'example:Group'),
        ...                 None)
        >>> verifyObject(IBeforeRemovingRelationshipEvent, event)
        True

    """

    implements(IBeforeRemovingRelationshipEvent)


class RelationshipRemovedEvent(RelationshipEvent):
    """A relationship has been broken.

        >>> from zope.interface.verify import verifyObject
        >>> event = RelationshipRemovedEvent('example:Membership',
        ...                                  ('a', 'example:Member'),
        ...                                  ('letters', 'example:Group'),
        ...                                  None)
        >>> verifyObject(IRelationshipRemovedEvent, event)
        True

    """

    implements(IRelationshipRemovedEvent)


def getRelatedObjects(obj, role, rel_type=None):
    """Return all objects related to `obj` with a given role."""
    return IRelationshipLinks(obj).getTargetsByRole(role, rel_type)


class RelationshipSchema(object):
    """Relationship schema.

    Boring doctest setup:

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.relationship.tests import SomeObject
        >>> setUp()
        >>> a = SomeObject('a')
        >>> b = SomeObject('b')

    Relationship schemas are syntactic sugar.  If you define a relationship
    schema like this:

        >>> from schooltool.relationship.tests import URIStub
        >>> URIMembership = URIStub('example:Membership')
        >>> URIMember = URIStub('example:Member')
        >>> URIGroup = URIStub('example:Group')
        >>> Membership = RelationshipSchema(URIMembership,
        ...                     member=URIMember, group=URIGroup)

    Then you can create, query and break relationships by writing

        >>> Membership(member=a, group=b)
        >>> Membership.query(group=b)
        [a]
        >>> Membership.unlink(member=a, group=b)

    instead of having to explicitly say

        >>> relate(URIMembership, (a, URIMember), (b, URIGroup))
        >>> getRelatedObjects(b, URIMember, rel_type=URIMembership)
        [a]
        >>> unrelate(URIMembership, (a, URIMember), (b, URIGroup))

    That's it.

        >>> tearDown()

    """

    implements(IRelationshipSchema)

    def __init__(self, rel_type, **roles):
        if len(roles) != 2:
            raise TypeError("A relationship must have exactly two ends.")
        self.rel_type = rel_type
        self.roles = roles

    def __call__(self, **parties):
        """Establish a relationship."""
        self._doit(relate, **parties)

    def unlink(self, **parties):
        """Break a relationship."""
        self._doit(unrelate, **parties)

    def query(self, **party):
        """Retrieve relationship targets."""
        if len(party) != 1:
            raise TypeError("A single party must be provided.")
        roles = list(self.roles.keys())
        my_role_key = party.keys()[0]
        roles.remove(my_role_key)
        other_role = self.roles[roles[0]]
        obj = party.values()[0]
        return getRelatedObjects(obj, other_role, rel_type=self.rel_type)

    def _doit(self, fn, **parties):
        """Extract and validate parties from keyword arguments and call fn."""
        (name_of_a, role_of_a), (name_of_b, role_of_b) = self.roles.items()
        try:
            a = parties.pop(name_of_a)
        except KeyError:
            raise TypeError('Missing a %r keyword argument.' % name_of_a)
        try:
            b = parties.pop(name_of_b)
        except KeyError:
            raise TypeError('Missing a %r keyword argument.' % name_of_b)
        if parties:
            raise TypeError("Too many keyword arguments.")
        fn(self.rel_type, (a, role_of_a), (b, role_of_b))


class RelationshipProperty(object):
    """Relationship property.

        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> setUp()
        >>> from schooltool.relationship.tests import URIStub

    Instead of calling global functions and passing URIs around you can define
    a property on an object and use it to create and query relationships:

        >>> class SomeClass(object):
        ...     implements(IAttributeAnnotatable)
        ...     friends = RelationshipProperty(URIStub('example:Friendship'),
        ...                                    URIStub('example:Friend'),
        ...                                    URIStub('example:Friend'))

    The property is introspectable, although that's not very useful

        >>> SomeClass.friends.rel_type.uri
        'example:Friendship'

        >>> SomeClass.friends.my_role.uri
        'example:Friend'

        >>> SomeClass.friends.other_role.uri
        'example:Friend'

    IRelationshipProperty defines things you can do with a relationship
    property.

        >>> from zope.interface.verify import verifyObject
        >>> someinstance = SomeClass()
        >>> verifyObject(IRelationshipProperty, someinstance.friends)
        True
        >>> tearDown()

    """

    def __init__(self, rel_type, my_role, other_role):
        self.rel_type = rel_type
        self.my_role = my_role
        self.other_role = other_role

    def __get__(self, instance, owner):
        """Bind the property to an instance."""
        if instance is None:
            return self
        else:
            return self.rel_type.bind(
                instance,
                self.my_role, self.rel_type, self.other_role)


class BoundRelationshipProperty(object):
    """Relationship property bound to an object."""

    implements(IRelationshipProperty)

    def __init__(self, this, rel_type, my_role, other_role):
        self.this = this
        self.rel_type = rel_type
        self.my_role = my_role
        self.other_role = other_role

    def __nonzero__(self):
        try:
            iter(self).next()
        except StopIteration:
            return False
        else:
            return True

    def __len__(self):
        count = 0
        for i in self:
            count += 1
        return count

    def __iter__(self):
        return iter(getRelatedObjects(self.this, self.other_role,
                                      self.rel_type))

    @property
    def relationships(self):
        linkset = IRelationshipLinks(self.this).getLinksByRole(self.other_role)
        return [RelationshipInfo(self.this, link)
                for link in linkset
                if link.rel_type == self.rel_type]

    def add(self, other, extra_info=None):
        """Establish a relationship between `self.this` and `other`."""
        relate(self.rel_type, (self.this, self.my_role),
                              (other, self.other_role), extra_info)

    def remove(self, other):
        """Unlink a relationship between `self.this` and `other`."""
        unrelate(self.rel_type, (self.this, self.my_role),
                                (other, self.other_role))


class RelationshipInfo(object):
    """Ugly implementation of access to relationship extra information.

    Setup:

        >>> from schooltool.relationship.tests import setUp, tearDown
        >>> from schooltool.relationship.tests import setUpRelationships
        >>> from schooltool.relationship.tests import SomeObject
        >>> from schooltool.relationship.tests import URIStub
        >>> setUp()
        >>> setUpRelationships()

    Say we relate two objects.

        >>> URIMembership = URIStub('example:Membership')
        >>> URIMember = URIStub('example:Member')
        >>> URIGroup = URIStub('example:Group')

        >>> a = SomeObject('a')
        >>> b = SomeObject('b')

        >>> relate(URIMembership, (a, URIMember), (b, URIGroup))

    Two links were created, one for each object.

        >>> link_to_b = list(IRelationshipLinks(a))[0]
        >>> link_to_a = list(IRelationshipLinks(b))[0]

    We will now construct a RelationshipInfo with object and it's link.

        >>> info_a = RelationshipInfo(a, link_to_b)
        >>> info_a.source
        a

        >>> info_a.target
        b

        >>> print info_a.extra_info
        None

    Setting extra_info updates both links.

        >>> info_a.extra_info = 'extra'
        >>> link_to_a.extra_info
        'extra'
        >>> link_to_b.extra_info
        'extra'

    That's it.

        >>> tearDown()

    """

    implements(IRelationshipInfo)

    def __init__(self, this, link_to_other):
        self._this = this
        self._link = link_to_other

    @property
    def source(self):
        return self._this

    @property
    def target(self):
        return self._link.target

    @property
    def state(self):
        return self._link.state

    @property
    def extra_info(self):
        return self._link.extra_info

    @extra_info.setter
    def extra_info(self, value):
        this_link = self._link

        links_of_target = IRelationshipLinks(self._link.target)
        # If links_of_target.find raises a ValueError, our data structures are
        # out of sync.
        other_link = links_of_target.find(
            this_link.role, self._this, this_link.my_role, this_link.rel_type)

        this_link.extra_info = value
        other_link.extra_info = value


class Link(Persistent, Contained):
    """One half of a relationship.

    A link is a simple class that holds information about one side of the
    relationship:

        >>> target = object()
        >>> my_role = 'example:Group'
        >>> role = 'example:Member'
        >>> rel_type = 'example:Membership'
        >>> link = Link(my_role, target, role, rel_type)
        >>> link.target is target
        True
        >>> link.my_role
        'example:Group'
        >>> link.role
        'example:Member'
        >>> link.rel_type
        'example:Membership'

    The attributes are documented in IRelationshipLink

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IRelationshipLink, link)
        True

    """

    implements(IRelationshipLink)

    shared_state = None

    def __init__(self, my_role, target, role, rel_type, extra_info=None):
        self.my_role = my_role
        self.target = target
        self.role = role
        self.rel_type = rel_type
        self.extra_info = extra_info

    @property
    def state(self):
        return self.rel_type.access(self.shared_state)


class LinkSet(Persistent, Contained):
    """Set of links.

    This class is used internally to represent relationships.  Initially it
    is empty

        >>> linkset = LinkSet()
        >>> list(linkset)
        []

    You can add new links to it

        >>> from schooltool.relationship.tests import URIStub
        >>> link1 = Link('example:Group', object(), URIStub('example:Member'),
        ...              URIStub('example:Membership'))
        >>> link2 = Link('example:Friend', object(), URIStub('example:Friend'),
        ...              URIStub('example:Friendship'))
        >>> linkset.add(link1)
        >>> linkset.add(link2)

    The links have landed in the cache too:

        >>> expected = {
        ...     'example:Member': [link1],
        ...     'example:Friend': [link2]}
        >>> dict(linkset._byrole.items()) == expected
        True

    Let's zap the cache and call getLinksByRole(), which should restore it:

        >>> del linkset._byrole
        >>> linkset.getLinksByRole(URIStub('something'))
        []

        >>> dict(linkset._byrole.items()) == expected
        True

    Links should get named:

        >>> link1.__name__
        '1'
        >>> link2.__name__
        '2'

    We can access our links through their names:

        >>> linkset['1'] is link1
        True
        >>> linkset['2'] is link2
        True

    And get parents set:

        >>> link1.__parent__ is linkset
        True

    We got them in the container now:

        >>> set(linkset) == set([link1, link2]) # order is not preserved
        True

    You can look for links for a specific relationship

        >>> linkset.find('example:Group',
        ...              link1.target,
        ...              URIStub('example:Member'),
        ...              URIStub('example:Membership')) is link1
        True

    We can't add same link into the container twice:

        >>> linkset.add(link1)                      # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        ValueError: ...

    If find fails, it raises ValueError, just like list.index.

        >>> linkset.find('example:Member', link1.target,
        ...              URIStub('example:Group'),
        ...              URIStub('example:Membership'))      # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        ValueError: ...

    You can remove links

        >>> linkset.remove(link2)
        >>> set(linkset) == set([link1])
        True

    The links are removed from the cache too:

        >>> list(linkset._byrole.keys())
        ['example:Member']

    If you try to remove a link that is not in the set, you will get a
    ValueError.

        >>> linkset.remove(link2)                   # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        ValueError: ...

    You can remove all links

        >>> linkset.clear()
        >>> set(linkset) == set([])
        True

    The cache has been cleared too:

        >>> len(linkset._byrole)
        0

    The class is documented in IRelationshipLinks

        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(IRelationshipLinks, linkset)
        True

    """

    implements(IRelationshipLinks)

    def __init__(self):
        self._links = OOBTree()
        self._byrole = OOBTree() # role -> list of links

    def getLinksByRole(self, role):
        """Get a set of links by role."""
        try:
            cache = self._byrole
        except AttributeError:
            cache = OOBTree()
            for link in self:
                cache.setdefault(link.role.uri, PersistentList()).append(link)
            self._byrole = cache

        return cache.get(role.uri, [])

    def add(self, link):
        if link.__parent__ == self:
            raise ValueError("You are adding same link twice.")

        i = 1
        while "%s" % i in self._links:
            i += 1
        link.__name__ = "%s" % i
        self._links[link.__name__] = link
        link.__parent__ = self

        self._byrole.setdefault(link.role.uri, PersistentList()).append(link)

    def remove(self, link):
        if link is self._links.get(link.__name__):
            del self._links[link.__name__]
            uri = link.role.uri
            self._byrole[uri].remove(link)
            if not self._byrole[uri]:
                del self._byrole[uri]
        else:
            raise ValueError("This link does not belong to this container!")

    def clear(self):
        self._links.clear()
        self._byrole.clear()

    def __iter__(self):
        return iter(self._links.values())

    def find(self, my_role, target, role, rel_type):
        links = self.getLinksByRole(role)
        for link in links:
            if (link.rel_type == rel_type and link.target is target
                and link.my_role == my_role):
                return link
        else:
            raise ValueError(my_role, target, role, rel_type)

    def __getitem__(self, id):
        return self._links[id]

    def get(self, key, default=None):
        return self._links.get(key, default)

    def getTargetsByRole(self, role, rel_type=None):
        links = self.getLinksByRole(role)
        if rel_type is None:
            return [link.target for link in links]
        else:
            return [link.target for link in links
                    if link.rel_type == rel_type]
