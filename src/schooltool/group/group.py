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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Group objects

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
__docformat__ = 'restructuredtext'
from persistent import Persistent

from zope.interface import implements
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import btree
from zope.app.container.contained import Contained

from schooltool.relationship import RelationshipProperty
from schooltool.app.membership import URIMembership, URIMember, URIGroup

from schooltool.group import interfaces


class GroupContainer(btree.BTreeContainer):
    """Container of groups."""

    implements(interfaces.IGroupContainer, IAttributeAnnotatable)


class Group(Persistent, Contained):
    """Group."""

    implements(interfaces.IGroup, interfaces.IGroupContained,
               IAttributeAnnotatable)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


def addGroupContainerToApplication(event):
    """Subscriber that adds a top-level groups container and a few groups."""
    event.object['groups'] = GroupContainer()
    event.object['groups']['manager'] = Group(u'Manager', u'Manager Group.')
