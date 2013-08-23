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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Group interfaces
"""

from zope.interface import Interface, Attribute
from zope.schema import TextLine, Text
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains, containers

from schooltool.common import SchoolToolMessage as _

class IGroupMember(Interface):
    """An object that knows the groups it is a member of."""

    groups = Attribute("""Groups (see IRelationshipProperty)""")


class IBaseGroup(Interface):
    """Group."""

    title = TextLine(
        title=_("Title"))

    description = Text(
        title=_("Description"),
        required=False)

    members = Attribute(
        """Members of the group (see IRelationshipProperty)""")


class IGroup(IBaseGroup):
    """Group."""


class IGroupContainer(IContainer):
    """Container of groups."""

    contains(IGroup)


class IGroupContained(IGroup, IContained):
    """Group contained in an IGroupContainer."""

    containers(IGroupContainer)


class IGroupContainerContainer(IContainer):
    """Container of group containers."""

    contains(IGroupContainer)
