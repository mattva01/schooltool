#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
The schooltool relationships.

$Id$
"""
from persistence import Persistent
from zope.interface import implements, classProvides
from schooltool.interfaces import IRemovableLink, IRelatable
from schooltool.interfaces import IRelationshipSchemaFactory
from schooltool.interfaces import IRelationshipSchema
from schooltool.interfaces import IRelationshipEvent
from schooltool.interfaces import IRelationshipAddedEvent
from schooltool.interfaces import IRelationshipRemovedEvent
from schooltool.interfaces import ISpecificURI
from schooltool.component import inspectSpecificURI, registerRelationship
from schooltool.event import EventMixin

__metaclass__ = type

class Link(Persistent):
    """A side (view) of a relationship belonging to one of the two
    ends of a relationship.

    An object of this class is in an invalid state until it is passed
    to a Relationship's constructor.
    """

    implements(IRemovableLink)

    def __init__(self, parent, role):
        inspectSpecificURI(role)
        if not IRelatable.isImplementedBy(parent):
            raise TypeError("Parent must be IRelatable (got %r)" % (parent,))
        self.__parent__ = parent
        self.role = role
        # self.relationship is set when this link becomes part of a
        # Relationship

    def _getTitle(self):
        return self.relationship.title

    def _setTitle(self, name):
        self.relationship.title = unicode(title)

    title = property(_getTitle, _setTitle)

    def _getReltype(self):
        return self.relationship.reltype

    reltype = property(_getReltype)

    def traverse(self):
        return self.relationship.traverse(self).__parent__

    def unlink(self):
        self.__parent__.__links__.remove(self)
        otherlink = self.relationship.traverse(self)
        self.traverse().__links__.remove(otherlink)
        event = RelationshipRemovedEvent((self, otherlink))
        event.dispatch(self.traverse())
        event.dispatch(otherlink.traverse())


class _LinkRelationship(Persistent):
    """A central part of a relationship.

    This an internal API for links.  Basically, it holds references to
    two links and its name.
    """

    def __init__(self, reltype, title, a, b):
        self.title = unicode(title)
        self.reltype = reltype
        self.a = a
        self.b = b
        a.relationship = self
        b.relationship = self
        assert IRelatable.isImplementedBy(a.__parent__)
        a.__parent__.__links__.add(a)
        assert IRelatable.isImplementedBy(b.__parent__)
        b.__parent__.__links__.add(b)

    def traverse(self, link):
        """Returns the link that is at the other end to the link passed in."""
        # Note that this will not work if link is proxied.
        if link is self.a:
            return self.b
        elif link is self.b:
            return self.a
        else:
            raise ValueError("Not one of my links: %r" % (link,))


class RelationshipSchema:
    classProvides(IRelationshipSchemaFactory)
    implements(IRelationshipSchema)

    def __init__(self, *reltype_and_optional_title, **roles):
        if len(reltype_and_optional_title) == 1:
            self.type, = reltype_and_optional_title
            self.title, doc = inspectSpecificURI(self.type)
        elif len(reltype_and_optional_title) == 2:
            self.type, self.title = reltype_and_optional_title
        else:
            raise TypeError("There can be either one or two positional"
                            " arguments. (got %r)"
                            % (reltype_and_optional_title,))
        if len(roles) != 2:
            raise TypeError("A relationship must have exactly two ends.")

        self.roles = roles

    def __call__(self, **parties):
        if len(self.roles) != len(parties):
            raise TypeError("Wrong number of parties to this relationship."
                            " Need %s, got %r" % (len(self.roles), parties))
        L = []
        for name, uri in self.roles.items():
            party = parties.pop(name, None)
            if party is None:
                raise TypeError("This relationship needs a %s party."
                                " Got %r" % (name, parties))
            L.append((party, uri))
        return relate(self.type, L[0], L[1], title=self.title)


def relate(reltype, (a, role_of_a), (b, role_of_b), title=None):
    """See IRelationshipAPI"""
    if title is None:
        title, doc = inspectSpecificURI(reltype)
    link_a = Link(a, role_of_b)
    link_b = Link(b, role_of_a)
    _LinkRelationship(reltype, title, link_a, link_b)
    return link_a, link_b


class RelationshipEvent(EventMixin):

    implements(IRelationshipEvent)

    def __init__(self, links):
        EventMixin.__init__(self)
        self.links = links


class RelationshipAddedEvent(RelationshipEvent):
    implements(IRelationshipAddedEvent)


class RelationshipRemovedEvent(RelationshipEvent):
    implements(IRelationshipRemovedEvent)


def relate_default(relationship_type, (a, role_a), (b, role_b), title=None):
    """See IRelationshipAPI.relate"""

    links = relate(relationship_type, (a, role_a), (b, role_b),
                   title=title)
    event = RelationshipAddedEvent(links)
    event.dispatch(a)
    event.dispatch(b)
    return links


def setUp():
    registerRelationship(ISpecificURI, relate_default)

