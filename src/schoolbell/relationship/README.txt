Relationship
============

schoolbell.relationship is a library for managing arbitrary many-to-many binary
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

You can also define relationship properties in your component classes, and
rewrite the example above as

    # Establish a relationship
    frogpond.members.add(frog)      # or frog.groups.add(frogpond)

    # Find all related objects for a given role (URIGroup in this case)
    for group in frogpond.members:
        print group


Details
-------

Relationship types and roles are identified by URIs (the idea was borrowed
from XLink and RDF).  You can use strings containing those URIs directly,
or you can use introspectable URI objects that also have an optional short name
and a description in addition to the URI itself.

    >>> from schoolbell.relationship import URIObject

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
Since schoolbell.relationship provides a default adapter from IAnnotatable
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
    >>> from schoolbell.relationship.tests import setUpRelationships
    >>> setUpRelationships()

You can create relationships by calling the `relate` function

    >>> from schoolbell.relationship import relate
    >>> frogs = SomeObject('frogs')
    >>> frogger = SomeObject('frogger')
    >>> relate(URIMembership, (frogs, URIGroup), (frogger, URIMember))

Since you will always want to use a particular set of roles for a given
relationship type, you can define a relationship schema and use it as a
shortcut:

    >>> from schoolbell.relationship import RelationshipSchema
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

    >>> from schoolbell.relationship import getRelatedObjects
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


Relationship properties
-----------------------

You can define a property in a class and use it instead of explicitly
calling global functions and passing roles around.

    >>> from schoolbell.relationship import RelationshipProperty

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

    >>> dogs.members.add(fido)

    >>> list(fido.groups)
    [dogs]
    >>> list(dogs.members)
    [fido]


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

    >>> from schoolbell.relationship.interfaces import IBeforeRelationshipEvent
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

    >>> from schoolbell.relationship.interfaces import IRelationshipAddedEvent
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

TODO: API to remove relationships
TODO: API to list all relationships?

Cleaning up:

    >>> zope.event.subscribers = old_subscribers
    >>> setup.placelessTearDown()

