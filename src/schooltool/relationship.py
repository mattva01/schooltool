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

import sets
from persistence import Persistent
from zope.interface import implements, classProvides, moduleProvides
from zope.interface import directlyProvides
from schooltool.db import PersistentPairKeysDictWithNames
from schooltool.db import MaybePersistentKeysSet
from schooltool.interfaces import IRemovableLink, IRelatable, IQueryLinks
from schooltool.interfaces import ILinkSet, ILink, IPlaceholder
from schooltool.interfaces import IRelationshipSchemaFactory
from schooltool.interfaces import IRelationshipSchema
from schooltool.interfaces import IRelationshipEvent
from schooltool.interfaces import IRelationshipAddedEvent
from schooltool.interfaces import IRelationshipRemovedEvent
from schooltool.interfaces import IRelationshipValencies
from schooltool.interfaces import IFaceted, ISchemaInvocation
from schooltool.interfaces import IModuleSetup, IValency
from schooltool.interfaces import IUnlinkHook, IMultiContainer
from schooltool.uris import ISpecificURI, inspectSpecificURI, strURI
from schooltool.component import getPath, registerRelationship
from schooltool import component
from schooltool.event import EventMixin

moduleProvides(IModuleSetup)

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
        if not IRelatable.providedBy(parent):
            raise TypeError("Parent must be IRelatable (got %r)" % (parent,))
        self.__parent__ = parent
        self.__name__ = None
        self.role = role
        self.callbacks = MaybePersistentKeysSet()
        # self.relationship is set when this link becomes part of a
        # Relationship

    def _getTitle(self):
        # XXX this is an ad-hoc bogosity (who said a link's target has a
        #     title?) that will need to be rethought later
        return self.traverse().title

    title = property(_getTitle)

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
        directlyProvides(event, self.reltype)
        event.dispatch(self.traverse())
        event.dispatch(otherlink.traverse())
        self._notifyCallbacks()
        otherlink._notifyCallbacks()

    def _notifyCallbacks(self):
        for callback in self.callbacks:
            if IUnlinkHook.providedBy(callback):
                callback.notifyUnlinked(self)
            else:
                callback(self)
        self.callbacks.clear()

    def registerUnlinkCallback(self, callback):
        if IUnlinkHook.providedBy(callback) or callable(callback):
            # this also has the nice side effect of notifying persistence that
            # self has changed
            self.callbacks.add(callback)
        else:
            raise TypeError("Callback must provide IUnlinkHook or be"
                            " callable. Got %r." % (callback,))


class _LinkRelationship(Persistent):
    """A central part of a relationship.

    This an internal API for links.  Basically, it holds references to
    two links and its name.
    """

    def __init__(self, reltype, a, b):
        self.reltype = reltype
        self.a = a
        self.b = b
        a.relationship = self
        b.relationship = self
        assert IRelatable.providedBy(a.__parent__)
        a.__parent__.__links__.add(a)
        assert IRelatable.providedBy(b.__parent__)
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


def relate(reltype, (a, role_of_a), (b, role_of_b)):
    """Sets up a relationship between two IRelatables with
    Link-_LinkRelationship-Link structure.

    Returns links attached to objects a and b respectively.
    """

    link_a = Link(a, role_of_b)
    link_b = Link(b, role_of_a)
    _LinkRelationship(reltype, link_a, link_b)
    return link_a, link_b


class RelationshipSchema:
    classProvides(IRelationshipSchemaFactory)
    implements(IRelationshipSchema)

    def __init__(self, reltype, **roles):
        self.type = reltype
        if len(roles) != 2:
            raise TypeError("A relationship must have exactly two ends.")

        self.roles = roles

    def __call__(self, **parties):
        if len(self.roles) != len(parties):
            raise TypeError("Wrong number of parties to this relationship."
                            " Need %s, got %r" % (len(self.roles), parties))
        L, N = [], []
        for name, uri in self.roles.items():
            party = parties.pop(name, None)
            if party is None:
                raise TypeError("This relationship needs a %s party."
                                " Got %r" % (name, parties))
            L.append((party, uri))
            N.append(name)
        links = component.relate(self.type, L[0], L[1])
        return {N[1]: links[0], N[0]: links[1]}


class RelationshipEvent(EventMixin):

    implements(IRelationshipEvent)

    def __init__(self, links):
        EventMixin.__init__(self)
        self.links = links

    def __str__(self):
        event = self.__class__.__name__
        s = ["%s" % event]
        reltype = self.links[0].reltype
        if reltype is not None:
            s.append("reltype=%r" % strURI(reltype))
        title = self.links[0].title
        if title:
            s.append("title=%r" % title)
        for link in self.links:
            try:
                path = getPath(link.traverse())
            except TypeError:
                path = str(link.traverse())
            s.append("link=%r, %r"
                     % (strURI(link.role), path))
        return "\n    ".join(s) + '\n'


class RelationshipAddedEvent(RelationshipEvent):
    implements(IRelationshipAddedEvent)


class RelationshipRemovedEvent(RelationshipEvent):
    implements(IRelationshipRemovedEvent)


def defaultRelate(reltype, (a, role_of_a), (b, role_of_b)):
    """See IRelationshipFactory"""
    links = relate(reltype, (a, role_of_a), (b, role_of_b))
    event = RelationshipAddedEvent(links)
    directlyProvides(event, reltype)
    event.dispatch(a)
    event.dispatch(b)
    return links


class LinkSet:
    """Set of links."""
    # Note: add and addPlaceholder methods are type-checked because we care
    #       a lot about the type of objects in this set.

    implements(ILinkSet)

    def __init__(self):
        self._data = PersistentPairKeysDictWithNames()

    def add(self, link):
        """Add a link to the set.

        If an equivalent link (with the same reltype, role and target)
        already exists in the set, raises a ValueError.
        """
        if ILink.providedBy(link):
            key = (link.traverse(), (link.reltype, link.role))
            value = self._data.get(key)
            if value is None:
                self._data[key] = link
            elif IPlaceholder.providedBy(value):
                self._data[key] = link
                value.replacedBy(link)
            else:
                assert ILink.providedBy(value)
                raise ValueError('duplicate link', link)
        else:
            raise TypeError('link must provide ILink', link)

    def _removeLink(self, link):
        key = (link.traverse(), (link.reltype, link.role))
        try:
            value = self._data[key]
        except KeyError:
            raise ValueError('link not in set', link)

        if value is link:
            del self._data[key]
        else:
            raise ValueError('link not in set', link)

    def _removePlaceholder(self, placeholder):
        for key, value in self._data.iteritems():
            if value is placeholder:
                del self._data[key]
                break
        else:
            raise ValueError('placeholder not in set', placeholder)

    def remove(self, link_or_placeholder):
        """Remove a link from the set.

        If an equivalent link does not exist in the set, raises a ValueError.
        """
        if ILink.providedBy(link_or_placeholder):
            self._removeLink(link_or_placeholder)
        elif IPlaceholder.providedBy(link_or_placeholder):
            self._removePlaceholder(link_or_placeholder)
        else:
            raise TypeError('remove must be called with a link or a'
                            ' placeholder. Got %r' % (link_or_placeholder,))

    def __iter__(self):
        for value in self._data.itervalues():
            if ILink.providedBy(value):
                yield value

    def addPlaceholder(self, for_link, placeholder):
        """Add a placeholder to the set to fill the place of the given link.
        """
        if (ILink.providedBy(for_link) and
            IPlaceholder.providedBy(placeholder)):
            key = (for_link.traverse(), (for_link.reltype, for_link.role))
            if key in self._data:
                raise ValueError(
                    'Tried to add placeholder as duplicate for link',
                    for_link)
            self._data[key] = placeholder
        else:
            raise TypeError('for_link must be an ILink and placeholder must'
                            ' by an IPlaceholder', for_link, placeholder)

    def iterPlaceholders(self):
        """Returns an iterator over the placeholders in the set."""
        for value in self._data.itervalues():
            if IPlaceholder.providedBy(value):
                yield value

    def getLink(self, name):
        return self._data.valueForName(name)


class RelatableMixin(Persistent):

    implements(IRelatable, IQueryLinks, IMultiContainer)

    def __init__(self):
        self.__links__ = LinkSet()

    def listLinks(self, role=ISpecificURI):
        """See IQueryLinks"""
        result = []
        for link in self.__links__:
            if link.role.extends(role, False):
                result.append(link)
        return result

    def getRelativePath(self, obj):
        """See IMultiContainer"""
        if obj in self.__links__:
            return 'relationships/%s' % obj.__name__
        return obj.__name__

    def getLink(self, name):
        return self.__links__.getLink(name)


class RelationshipValenciesMixin(RelatableMixin):

    implements(IRelationshipValencies)

    valencies = ()

    def __init__(self):
        RelatableMixin.__init__(self)

    def _valency2invocation(self, valency):
        schema = valency.schema
        this = valency.keyword
        keywords = list(schema.roles.keys())
        if this not in keywords:
            raise ValueError("Incorrect key %r in valency %r used." %
                             (this, valency))
        keywords.remove(this)
        other = keywords[0]
        return {(schema.type, schema.roles[this]):
                SchemaInvocation(schema, this, other)}

    def getValencies(self):
        result = {}
        valencies = self.valencies
        if type(valencies) != type(()):
            valencies = (valencies,)
        for valency in valencies:
            result.update(self._valency2invocation(valency))
        if IFaceted.providedBy(self):
            all_facet_valencies = sets.Set()
            conflict = sets.Set()
            for facet in component.FacetManager(self).iterFacets():
                if (IRelationshipValencies.providedBy(facet)
                    and facet.active):
                    valencies = facet.getValencies()
                    facet_valencies = sets.Set(valencies.keys())
                    conflict |= all_facet_valencies & facet_valencies
                    all_facet_valencies |= facet_valencies
                    result.update(valencies)
            if conflict:
                raise TypeError("Conflicting facet valencies: %r" % conflict)
        return result


class SchemaInvocation:

    implements(ISchemaInvocation)

    def __init__(self, schema, this, other):
        self.schema = schema
        self.this = this
        self.other = other


class Valency:

    implements(IValency)

    def __init__(self, schema, keyword):
        self.schema = schema
        self.keyword = keyword


def setUp():
    """Register the default relationship handler."""
    registerRelationship(ISpecificURI, defaultRelate)

