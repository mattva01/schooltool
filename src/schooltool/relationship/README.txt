Relationship
============

schooltool.relationship is a library for managing arbitrary many-to-many binary
relationships.

Quick overview
--------------

This package lets you define arbitrary many-to-many relationship schemas and
use them to relate arbitrary components (that are annotatable or have an
adapter to IRelationshipLinks).

Usage example:

    # Establish a relationship
    Membership(member=frog, group=frogpond)

    # Find all related objects for a given role (URIGroup in this case)
    for group in getRelatedObjects(frog, URIGroup):
        print group

    Membership.unlink(member=frog, group=frogpond)

You can also define relationship properties in your component classes, and
rewrite the example above as

    # Establish a relationship
    frogpond.members.add(frog)      # or frog.groups.add(frogpond)

    # Find all related objects for a given role (URIGroup in this case)
    for group in frogpond.members:
        print group

    # Remove a relationship
    frogpond.members.remove(frog)   # or frog.groups.remove(frogpond)


Dependencies
------------

- zope.interface
- zope.schema
- zope.event
- ZODB (persistent and persistent.list)
- zope.app (only if you want to use the provided adapter for IAnnotatable,
  and the provided event handlers for object change events)


Details
-------

Relationship types and roles are identified by URIs (the idea was borrowed
from XLink and RDF).  You can use strings containing those URIs directly,
or you can use introspectable URI objects that also have an optional short name
and a description in addition to the URI itself.

    >>> from schooltool.relationship import URIObject

For example, a generic group membership relationship can be defined with the
following URIs:

    >>> URIMembership = URIObject('http://schooltool.org/ns/membership',
    ...                           'Membership', 'The membership relationship.')
    >>> URIGroup = URIObject('http://schooltool.org/ns/membership/group',
    ...                      'Group', 'A role of a containing group.')
    >>> URIMember = URIObject('http://schooltool.org/ns/membership/member',
    ...                       'Member', 'A group member role.')

To demonstrate relationships we need some objects that can be related.  Any
object that has an adapter to IRelationshipLinks can be used in relationships.
Since schooltool.relationship provides a default adapter from IAnnotatable
to IRelationshipLinks, it is enough to declare that our objects are
IAttributeAnnotatable.

    >>> from zope.interface import implements
    >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
    >>> class SomeObject(object):
    ...     implements(IAttributeAnnotatable)
    ...     def __init__(self, name):
    ...         self._name = name
    ...     def __repr__(self):
    ...         return self._name

We need some setup to make Zope 3 annotations work.

    >>> from zope.app.tests import setup
    >>> setup.placelessSetUp()
    >>> setup.setUpAnnotations()

We need to define the adapter from IAnnotatable to IRelationshipLinks.
In real life you would include the ZCML configuration of the
'schooltool.relationship' package via Zope 3 package includes.  In a test
you can use setUpRelationships from schooltool.relationship.tests.

    >>> from schooltool.relationship.tests import setUpRelationships
    >>> setUpRelationships()

You can create relationships by calling the `relate` function

    >>> from schooltool.relationship import relate
    >>> frogs = SomeObject('frogs')
    >>> frogger = SomeObject('frogger')
    >>> relate(URIMembership, (frogs, URIGroup), (frogger, URIMember))

Since you will always want to use a particular set of roles for a given
relationship type, you can define a relationship schema and use it as a
shortcut:

    >>> from schooltool.relationship import RelationshipSchema
    >>> Membership = RelationshipSchema(URIMembership, group=URIGroup,
    ...                                 member=URIMember)

    >>> lilfroggy = SomeObject('lilfroggy')
    >>> Membership(member=lilfroggy, group=frogs)

If you try to create the same relationship between the same objects more
than once, you will get a DuplicateRelationship exception.

    >>> Membership(member=lilfroggy, group=frogs)
    Traceback (most recent call last):
      ...
    DuplicateRelationship

You can query relationships by calling the `getRelatedObjects` function.
It returns a list of objects in undefined order, so we'll define a function
to sort them alphabetically:

    >>> def sorted(list):
    ...     items = [(repr(item), item) for item in list]
    ...     items.sort()
    ...     return [row[-1] for row in items]

For example, you can get a list of all members of the `frogs` group like
this:

    >>> from schooltool.relationship import getRelatedObjects
    >>> sorted(getRelatedObjects(frogs, URIMember))
    [frogger, lilfroggy]

The relationship is bidirectional, so you can ask an object what groups it
belongs to

    >>> getRelatedObjects(frogger, URIGroup)
    [frogs]

You can also explicitly say that you want all URIGroups that participate
in a URIMembership relationship.

    >>> getRelatedObjects(frogger, URIGroup, URIMembership)
    [frogs]
    >>> getRelatedObjects(frogger, URIGroup, 'example:Groupship')
    []

In general, avoid reusing the same role for different relationship types.

You can remove relationships by calling the `unrelate` function

    >>> from schooltool.relationship import unrelate
    >>> unrelate(URIMembership, (frogs, URIGroup), (frogger, URIMember))

    >>> getRelatedObjects(frogger, URIGroup)
    []
    >>> getRelatedObjects(frogs, URIMember)
    [lilfroggy]

If you try to remove a relationship that does not exist, you will get an
exception

    >>> unrelate(URIMembership, (frogs, URIMember), (frogger, URIGroup))
    Traceback (most recent call last):
      ...
    NoSuchRelationship

If you have a relationship schema, you can call its `unlink` method, as
a shortcut for the full unrelate call.

    >>> Membership.unlink(member=lilfroggy, group=frogs)
    >>> getRelatedObjects(frogs, URIMember)
    []

There is also an `unrelateAll` function that removes all relationships of
an object.  It is useful if you want to break all relationships when deleting
an object.


Relationship properties
-----------------------

You can define a property in a class and use it instead of explicitly
calling global functions and passing roles around.

    >>> from schooltool.relationship import RelationshipProperty

    >>> class Group(SomeObject):
    ...     members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    >>> class Member(SomeObject):
    ...     groups = RelationshipProperty(URIMembership, URIMember, URIGroup)

Usage example:

    >>> fido = Member('fido')
    >>> dogs = Group('dogs')

    >>> list(fido.groups)
    []
    >>> list(dogs.members)
    []

    >>> bool(fido.groups)
    False

    >>> dogs.members.add(fido)

    >>> list(fido.groups)
    [dogs]
    >>> list(dogs.members)
    [fido]

    >>> bool(fido.groups)
    True
    >>> len(fido.groups)
    1

    >>> fido.groups.remove(dogs)

    >>> list(fido.groups)
    []
    >>> list(dogs.members)
    []


Events
------

    >>> import zope.event
    >>> old_subscribers = zope.event.subscribers
    >>> zope.event.subscribers = []

Before you establish a relationship, a BeforeRelationshipEvent is sent out.
You can implement constraints by raising an exception in an event subscriber.

    >>> from zope.interface import Interface, directlyProvides
    >>> class IFrog(Interface):
    ...     pass

    >>> from schooltool.relationship.interfaces import IBeforeRelationshipEvent
    >>> def no_toads(event):
    ...     if (IBeforeRelationshipEvent.providedBy(event) and
    ...             event.rel_type == URIMembership and
    ...             event[URIGroup] is frogs and
    ...             not IFrog.providedBy(event[URIMember])):
    ...         raise Exception("Only frogs can be members of the frogs group")
    >>> zope.event.subscribers.append(no_toads)

    >>> toady = SomeObject('toady')
    >>> Membership(member=toady, group=frogs)
    Traceback (most recent call last):
      ...
    Exception: Only frogs can be members of the frogs group

When you establish a relationship, a RelationshipAddedEvent is sent out.

    >>> from schooltool.relationship.interfaces import IRelationshipAddedEvent
    >>> def my_subscriber(event):
    ...     if IRelationshipAddedEvent.providedBy(event):
    ...         print 'Relationship %s added between %s (%s) and %s (%s)' % (
    ...                     event.rel_type.name,
    ...                     event.participant1, event.role1.name,
    ...                     event.participant2, event.role2.name)
    >>> zope.event.subscribers.append(my_subscriber)

    >>> kermit = SomeObject('kermit')
    >>> directlyProvides(kermit, IFrog)
    >>> Membership(member=kermit, group=frogs)
    Relationship Membership added between kermit (Member) and frogs (Group)

Before you break a relationship, a BeforeRemovingRelationshipEvent is sent out.
You can implement constraints by raising exceptions in the subscriber (e.g.
prevent members from leaving a group before they do something they have to
do).

When you break a relationship, a RelationshipRemovedEvent is sent out.

    >>> from schooltool.relationship.interfaces \
    ...         import IBeforeRemovingRelationshipEvent
    >>> from schooltool.relationship.interfaces \
    ...         import IRelationshipRemovedEvent
    >>> def my_subscriber(event):
    ...     if IBeforeRemovingRelationshipEvent.providedBy(event):
    ...         if event[URIMember] is kermit:
    ...             print "Please don't leave us!"
    ...     if IRelationshipRemovedEvent.providedBy(event):
    ...         print 'Relationship %s between %s (%s) and %s (%s) removed' % (
    ...                     event.rel_type.name,
    ...                     event.participant1, event.role1.name,
    ...                     event.participant2, event.role2.name)
    >>> zope.event.subscribers.append(my_subscriber)

    >>> Membership.unlink(member=kermit, group=frogs)
    Please don't leave us!
    Relationship Membership between kermit (Member) and frogs (Group) removed


Symmetric relationships
-----------------------

Symmetric relationships work too:

    >>> URIFriendship = URIObject('example:Friendship', 'Friendship')
    >>> URIFriend = URIObject('example:Friend', 'Friend')

    >>> Friendship = RelationshipSchema(URIFriendship,
    ...                                 one=URIFriend, other=URIFriend)
    >>> Friendship(one=fido, other=kermit)
    Relationship Friendship added between kermit (Friend) and fido (Friend)

    >>> class FriendlyObject(SomeObject):
    ...     friends = RelationshipProperty(URIFriendship, URIFriend, URIFriend)

    >>> neko = FriendlyObject('neko')
    >>> neko.friends.add(kermit)
    Relationship Friendship added between neko (Friend) and kermit (Friend)
    >>> list(neko.friends)
    [kermit]
    >>> sorted(getRelatedObjects(kermit, URIFriend))
    [fido, neko]

Note that if you use symmetric relationships, you cannot use `__getitem__`
on IBeforeRelationshipEvents.


Annotated relationships
-----------------------

Sometimes you may want to attach some extra information to a relationship (e.g.
a label).  You can do so by passing an extra argument to `relate` and
`unrelate`:

    >>> relate(URIFriendship, (kermit, URIFriend), (frogger, URIFriend),
    ...        'kermit and frogger know each other for years')
    Relationship Friendship added between kermit (Friend) and frogger (Friend)

This extra argument should be either a read-only object, or a subclass of
persistent.Persistent, because references to this object will be stored from
both relationship sides.

You can access this extra information from relationship links directly:

    >>> from schooltool.relationship.interfaces import IRelationshipLinks
    >>> for link in IRelationshipLinks(kermit):
    ...     if link.extra_info:
    ...         print link.extra_info
    kermit and frogger know each other for years

Since this is very inconvenient, I expect you will write your own access
properties that mimic RelationshipProperty, and override the `__iter__`
method.  For example:

    >>> from schooltool.relationship.relationship import BoundRelationshipProperty
    >>> class FriendshipProperty(object):
    ...     def __get__(self, instance, owner):
    ...         if instance is None: return self
    ...         return BoundFriendshipProperty(instance)
    >>> class BoundFriendshipProperty(BoundRelationshipProperty):
    ...     def __init__(self, this):
    ...         BoundRelationshipProperty.__init__(self, this, URIFriendship,
    ...                                            URIFriend, URIFriend)
    ...     def __iter__(self):
    ...         for link in IRelationshipLinks(self.this):
    ...             if link.role == self.other_role and link.rel_type == self.rel_type:
    ...                 yield link.target, link.extra_info

You can then use it like this:

    >>> class Friend(SomeObject):
    ...     friends = FriendshipProperty()

    >>> fluffy = Friend('fluffy')
    >>> fluffy.friends.add(kermit,
    ...         'fluffy just met kermit, but fluffy is very friendly')
    Relationship Friendship added between fluffy (Friend) and kermit (Friend)

    >>> for friend, extra_info in fluffy.friends:
    ...     print '%s: %s' % (friend, extra_info)
    kermit: fluffy just met kermit, but fluffy is very friendly


Caveats
-------

- When you delete objects, you should remove all relationships for those
  objects.  If you use Zope 3 objects events, you can register the
  `unrelateOnDeletion` event handler from schooltool.relationship.objectevents.
  configure.zcml of schooltool.relationship does that.

- When you copy objects (e.g. using Zope's IObjectCopier), you should take
  care to ensure that you do not duplicate just one half of relationship
  links.  It is tricky.  locationCopy from zope.app.location.pickling
  performs deep copies of all objects that are located within the object you
  are copying.  It works if all relationships are within this subtree (or
  outside it).  You will get problems if you have a relationship between
  an object that is copied and another object that is not copied.

  You can register the `unrelateOnCopy` event handler from
  schooltool.relationship.objectevents to solve *part* of the problem
  (configure.zcml of schooltool.relationship does that).  This event handler
  removes all relationships from the copy of the object that you are copying.
  It does not traverse the whole deply-copied subtree, therefore if you
  have subobjects that participate in relationships with objects outside of
  the subtree, you will have problems.

  An alternative solution is to disallow copying of objects that may have
  subobjects related with other objects that are not located within the
  original object.  To do so, declare and IObjectCopier adapter for the object
  and make the `copyable` method return False.


Cleaning up
-----------

    >>> zope.event.subscribers = old_subscribers
    >>> setup.placelessTearDown()

