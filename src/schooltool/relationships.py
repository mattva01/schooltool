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
from schooltool.interfaces import ILink
from schooltool.component import inspectSpecificURI

__metaclass__ = type

class Link(Persistent):
    """A side (view) of a relationship beelonging to one of the two
    ends of a relationship.

    An object of this class is in an invalid state until it is passed
    to a Relationship's constructor.
    """

    implements(ILink)

    def __init__(self, parent, role):
        inspectSpecificURI(role)
        self.__parent__ = parent
        self.role = role

    # These attributes are set when being added to a relationship
    rel = None
    other = None

    def _getTitle(self):
        return self.rel.title

    def _setTitle(self, name):
        self.rel.title = unicode(title)

    title = property(_getTitle, _setTitle)

    def traverse(self):
        return getattr(self.rel, self.other).__parent__

class Relationship(Persistent):
    """A central part of a relationship.

    Basically, it holds references to two links and its name.
    """

    def __init__(self, title, a, b):
        self.title = unicode(title)
        self.a = a
        self.b = b
        a.rel = self
        b.rel = self
        a.other = 'b'
        b.other = 'a'
