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
from persistence.list import PersistentList
from zope.interface import implements, classProvides, moduleProvides
from zope.interface import directlyProvides
from schooltool.db import PersistentPairKeysDict
from schooltool.db import MaybePersistentKeysSet
from schooltool.interfaces import IRemovableLink, IRelatable, IQueryLinks
from schooltool.interfaces import ILinkSet, ILink, IPlaceholder
from schooltool.interfaces import IRelationshipSchemaFactory
from schooltool.interfaces import IRelationshipSchema
from schooltool.interfaces import IRelationshipEvent
from schooltool.interfaces import IRelationshipAddedEvent
from schooltool.interfaces import IRelationshipRemovedEvent
from schooltool.interfaces import IRelationshipValencies
from schooltool.interfaces import ISpecificURI, IFaceted
from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IUnlinkHook
from schooltool.component import inspectSpecificURI, registerRelationship
from schooltool.component import strURI, getPath
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
        if not IRelatable.isImplementedBy(parent):
            raise TypeError("Parent must be IRelatable (got %r)" % (parent,))
        self.__parent__ = parent
        self.role = role
        self.callbacks = MaybePersistentKeysSet()
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
        directlyProvides(event, self.reltype)
        event.dispatch(self.traverse())
        event.dispatch(otherlink.traverse())
        self._notifyCallbacks()
        otherlink._notifyCallbacks()

    def _notifyCallbacks(self):
        for callback in self.callbacks:
            if IUnlinkHook.isImplementedBy(callback):
                callback.notifyUnlinked(self)
            else:
                callback(self)
        self.callbacks.clear()

    def registerUnlinkCallback(self, callback):
        if IUnlinkHook.isImplementedBy(callback) or callable(callback):
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


def relate(reltype, (a, role_of_a), (b, role_of_b), title=None):
    """Sets up a relationship between two IRelatables with
    Link-_LinkRelationship-Link structure.

    Returns links attached to objects a and b respectively.
    """

    if title is None:
        title, doc = inspectSpecificURI(reltype)
    link_a = Link(a, role_of_b)
    link_b = Link(b, role_of_a)
    _LinkRelationship(reltype, title, link_a, link_b)
    return link_a, link_b


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
        L, N = [], []
        for name, uri in self.roles.items():
            party = parties.pop(name, None)
            if party is None:
                raise TypeError("This relationship needs a %s party."
                                " Got %r" % (name, parties))
            L.append((party, uri))
            N.append(name)
        links = component.relate(self.type, L[0], L[1], title=self.title)
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


def defaultRelate(reltype, (a, role_of_a), (b, role_of_b), title=None):
    """See IRelationshipFactory"""
    links = relate(reltype, (a, role_of_a), (b, role_of_b), title)
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
        self._data = PersistentPairKeysDict()

    def add(self, link):
        """Add a link to the set.

        If an equivalent link (with the same reltype, role and target)
        already exists in the set, raises a ValueError.
        """
        if ILink.isImplementedBy(link):
            key = (link.traverse(), (link.reltype, link.role))
            value = self._data.get(key)
            if value is None:
                self._data[key] = link
            elif IPlaceholder.isImplementedBy(value):
                self._data[key] = link
                value.replacedBy(link)
            else:
                assert ILink.isImplementedBy(value)
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
        if ILink.isImplementedBy(link_or_placeholder):
            self._removeLink(link_or_placeholder)
        elif IPlaceholder.isImplementedBy(link_or_placeholder):
            self._removePlaceholder(link_or_placeholder)
        else:
            raise TypeError('remove must be called with a link or a'
                            ' placeholder. Got %r' % (link_or_placeholder,))

    def __iter__(self):
        for value in self._data.itervalues():
            if ILink.isImplementedBy(value):
                yield value

    def addPlaceholder(self, for_link, placeholder):
        """Add a placeholder to the set to fill the place of the given link.
        """
        if (ILink.isImplementedBy(for_link) and 
            IPlaceholder.isImplementedBy(placeholder)):
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
            if IPlaceholder.isImplementedBy(value):
                yield value


class RelatableMixin(Persistent):

    implements(IRelatable, IQueryLinks)

    def __init__(self):
        self.__links__ = LinkSet()

    def listLinks(self, role=ISpecificURI):
        result = []
        for link in self.__links__:
            if link.role.extends(role, False):
                result.append(link)
        return result


class RelationshipValenciesMixin(RelatableMixin):

    implements(IRelationshipValencies)

    def __init__(self):
        RelatableMixin.__init__(self)
        self._valencies = PersistentList()

    def getValencies(self):
        result = []
        result += self._valencies
        if IFaceted.isImplementedBy(self):
            for facet in component.FacetManager(self).iterFacets():
                if (IRelationshipValencies.isImplementedBy(facet)
                    and facet.active):
                    result += facet.getValencies()
        return result


def setUp():
    """Register the default relationship handler."""
    registerRelationship(ISpecificURI, defaultRelate)

