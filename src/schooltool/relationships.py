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
from persistence.dict import PersistentDict
from zope.interface import implements
from schooltool.interfaces import IRemovableLink, IRelatable
from schooltool.component import inspectSpecificURI

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

    def traverse(self):
        return self.relationship.traverse(self).__parent__

    def unlink(self):
        self.__parent__.__links__.remove(self)
        otherlink = self.relationship.traverse(self)
        self.traverse().__links__.remove(otherlink)


class _Relationship(Persistent):
    """A central part of a relationship.

    This an internal API for links.  Basically, it holds references to
    two links and its name.
    """

    def __init__(self, title, a, b):
        self.title = unicode(title)
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


def relate(title, a, role_a, b, role_b):
    """See IRelationshipAPI"""
    link_a = Link(a, role_b)
    link_b = Link(b, role_a)
    _Relationship(title, link_a, link_b)
    return link_a, link_b

