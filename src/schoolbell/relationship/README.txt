Relationship
============

schoolbell.relationship is a library for managing arbitrary many-to-many binary
relationships.

Relationship types and roles are identified by URIs (the idea was borrowed
from XLink and RDF).  Instead of dealing with strings directly,
schoolbell.relationship uses introspectable URI objects that also have an
optional short name and a description in addition to the URI itself.

    >>> from schoolbell.relationship import URIObject

For example, a generic group membership relationship can be defined with the
following URIs:

    >>> URIMembership = URIObject('http://schooltool.org/ns/membership',
    ...                           'Membership', 'The membership relationship.')
    >>> URIGroup = URIObject('http://schooltool.org/ns/membership/group')
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

You can query relationships by calling the `getRelatedObjects` function.
For example, you can get a list of all members of the `frogs` group like
this:

    >>> from schoolbell.relationship import getRelatedObjects
    >>> getRelatedObjects(frogs, URIMember)
    [frogger, lilfroggy]

The relationship is bidirectional, so you can ask an object what groups it
belongs to

    >>> getRelatedObjects(frogger, URIGroup)
    [frogs]



TODO: API to remove relationships
TODO: API to list all relationships?
TODO: events

Cleaning up:

    >>> setup.placelessTearDown()

