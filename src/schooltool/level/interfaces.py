#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Level interfaces.
"""

import zope.schema
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains, containers
from zope.interface import Interface, Attribute

from schooltool.common import SchoolToolMessage as _


class ILevel(Interface):
    """A level of learing (basically Nth year of courses)."""

    title = zope.schema.TextLine(
        title=_("Title"))

    courses = Attribute(
        """Courses available for this level.
           see schooltool.relationship.interfaces.IRelationshipProperty.""")


class ILevelContainer(IContainer):
    """Container of levels."""

    contains(ILevel)


class ILevelContained(ILevel, IContained):
    """Level contained in an ILevelContainer."""

    containers(ILevelContainer)


class ILevelContainerContainer(IContainer):
    """Container of level containers."""

    contains(ILevelContainer)
