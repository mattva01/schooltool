#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
SchoolTool interfaces for the relationship system.

$Id$
"""

from zope.interface import Interface
from zope.schema import Object, TextLine, Set, Tuple, Dict, BytesLine
from zope.app.location.interfaces import ILocation
from schooltool.interfaces.uris import IURIObject


class ILinkSet(ILocation):
    """A set of links.

    Raises ValueError on an attempt to add duplicate members.

    Links with the same reltype, role and target are considered to be
    equal, for purposes of set membership.

    So, a link is a duplicate member if it has the same reltype, role and
    target as an existing member.
    """

    def add(link):
        """Add a link to the set.

        If an equivalent link (with the same reltype, role and target)
        already exists in the set, raises a ValueError.

        If an equivalent placeholder is in the set, replace the placeholder
        with the link, and call IPlaceholder.replacedBy(link).
        """

    def addPlaceholder(for_link, placeholder):
        """Add a placeholder to the set to fill the place of the given link.
        """

    def iterPlaceholders():
        """Return an iterator over the placeholders in the set."""

    def remove(link_or_placeholder):
        """Remove a link or a placeholder from the set.

        If the given object is not in the set, raises a ValueError.
        The error is raised even if there is an equivalent link in the set.
        """

    def __iter__():
        """Return an iterator over the links in the set."""

    def getLink(name):
        """Returns a link by a name"""


class IRelatable(ILocation):
    """An object which can take part in relationships."""

    __links__ = Set(
        title=u"A set of link sets.",
        value_type=Object(title=u"A link set", schema=ILinkSet))

    def getLink(name):
        """Return a link by a name within this relatable."""


class ILink(ILocation):
    """A link is a 'view' of a relationship the relating objects have.

             A<--->Link<---->Relationship<---->Link<--->B

    """

    __parent__ = Object(
        title=u"The container that this link resides in.",
        schema=IRelatable)

    __name__ = TextLine(
        title=u"Unique name within the link container.")

    source = Object(
        title=u"The object that this link points from.",
        schema=IRelatable)

    target = Object(
        title=u"The object at the other end of the relationship",
        readonly=True,
        schema=IRelatable)

    reltype = Object(
        title=u"The SpecificURI of the relationship type.",
        schema=IURIObject)

    title = TextLine(
        title=u"The title of the target of the link.")

    role = Object(
        title=u"The role implied by traversing this link.",
        schema=IURIObject,
        description=u"""
        This is how the target relates to this link's source.
        """)


class IRemovableLink(ILink):

    def unlink():
        """Remove a link.

        Also removes the opposite direction of the relationship if the
        relationship is bidirectional.

        Sends a IRelationshipRemovedEvent to both previous participants
        of the relationship after the relationship has been broken.
        """

    def registerUnlinkCallback(callback):
        """Register an object that is notified after the link is unlinked.

        The callback must conform to IUnlinkHook and be pickleable.

        All callbacks will be unregistered when unlink is called.
        Callbacks are a set. If you register an identical callback more than
        once, it will still be called only once.
        """


class IUnlinkHook(Interface):

    def notifyUnlinked(link):
        """The given link was unlinked."""


class IPlaceholder(Interface):
    """A placeholder for a link."""

    def replacedBy(link):
        """The placeholder was replaced in the link set by the given link."""


class IQueryLinks(Interface):
    """An interface for querying a collection of links for those that
    meet certain conditions.
    """

    def listLinks(role=None):
        """Return all the links (matching a specified role, if specified)."""


class IRelationshipSchema(Interface):
    """Object that represents a relationship."""

    type = Object(
        title=u"A URI for the type of this relationship.",
        schema=IURIObject)

    roles = Dict(
        title=u"Roles",
        key_type=TextLine(title=u"Symbolic parameter name"),
        value_type=Object(schema=IURIObject),
        description=u"""
        A mapping of symbolic parameter names which this schema expects
        to respective URIs.
        """)

    def __call__(**parties):
        """Relate the parties to the relationship.

        The objects are related according to the roles indicated
        by the keyword arguments.

        Returns a dict of {role_name: link}.
        """


class IValency(Interface):
    """An object signifying that the owner can participate in a
    certain relationship schema in a certain role.
    """

    schema = Object(
        title=u"A relationship schema",
        schema=IRelationshipSchema)

    keyword = BytesLine(
        title=u"A keyword argument the schema takes for this object")


class IRelationshipValencies(Interface):
    """Give information on what relationships are pertinent to this object."""

    valencies = Tuple(
        title=u"A tuple of IValency objects",
        value_type=Object(schema=IValency))

    def getValencies():
        """Return a mapping of valencies.

        The return value is a dictionary with tuples containing the
        relationship type (as an IURIObject) and the role of this
        object (also an IURIObject) as keys, and ISchemaInvocation
        objects as values.
        """


class ISchemaInvocation(Interface):
    """An object describing how to call a relationship schema for a valency"""

    schema = Object(
        title=u"A relationship schema",
        schema=IRelationshipSchema)

    this = BytesLine(
        title=u"A keyword argument the schema takes for this object")

    other = BytesLine(
        title=u"A keyword argument the schema takes for the other object")


class IRelationshipSchemaFactory(Interface):

    def __call__(relationship_type, optional_title, **roles):
        """Create an IRelationshipSchema of relationship_type.

        Use keyword arguments to say what roles are required when
        creating such a relationship.

        The relationship type must be given. However, the title is
        optional, and defaults to the URI of the relationship type.
        """


class IRelationshipFactory(Interface):
    """Factory that establishes relationships of a certain type."""

    def __call__(relationship_type, (a, role_a), (b, role_b), title=None):
        """Relate a and b via the roles and the relationship type.

        Returns a tuple of links attached to a and b respectively.

        Sends a IRelationshipAddedEvent to both a and b after the
        relationship has been established.
        """


class IRelationshipAPI(Interface):

    def relate(relationship_type, (a, role_a), (b, role_b)):
        """Relate a and b via the roles and the relationship_type.

        Returns a tuple of links attached to a and b respectively.

        Sends a IRelationshipAddedEvent to both participants of the
        relationship after the relationship has been established.

        This function is implemented by looking up a relation factory
        by the relationship_type.

        Example::
                        my report
              /------------------------->
          officer  relationship_type  soldier
              <-------------------------/
                       my superior

        relate(URICommand,
               (officer, URIMySuperior),
               (soldier, URIMyReport))

        Returns a two-tuple of:
          * The link traversable from the officer, role is URIMyReport
          * The link traversable from the soldier, role is URIMySuperior

        If title is not given, the title links defaults to the
        relationship_type URI.
        """

    def getRelatedObjects(obj, role):
        """Return a sequence of object's relationships with a given role.

        Calling getRelatedObjects(obj, role) is equivalent to the following
        list comprehension::

            [link.target for link in obj.listLinks(role)]
        """

    def registerRelationship(relationship_type, factory):
        """Register a relationship type.

        relationship_type is an IURIObject (or None if you're registering the
        default handler).

        factory is an IRelationshipFactory.

        This function does nothing if the same registration is attempted the
        second time.

        When IRelationshipAPI.relate is called, it will find the handler for
        the relationship type (falling back to the default handler) and defer
        to that.
        """


