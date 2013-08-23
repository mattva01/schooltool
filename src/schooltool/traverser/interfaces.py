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
Pluggable Traverser Interfaces

This implementation is independent of the presentation type. Sub-interfaces
must be written for every specific presentation type.
"""

from zope.interface import Interface, Attribute
from zope.publisher.interfaces import IPublishTraverse


class IPluggableTraverser(IPublishTraverse):
    """A pluggable traverser.

    This traverser traverses a name by utilizing helper traversers that are
    registered as ``ITraverserPlugin`` subscribers.
    """


class ISchoolToolTraverser(Interface):
    """A plugin for the pluggable traverser."""

    context = Attribute("The context object the plugin traverses")
    request = Attribute("The request object driving the traversal")

    def traverse(name):
        """The 'name' argument is the name that is to be looked up; it must
        be an ASCII string or Unicode object.

        If a lookup is not possible, raise a NotFound error.

        This method should return an object having the specified name and
        `self` as parent.
        """


class ITraverser(IPublishTraverse,
                 ISchoolToolTraverser):
    """A simple traverser.

    This traverser traverses a name by utilizing helper traversers that are
    registered as ``ITraverserPlugin`` subscribers.
    """


class ITraverserPlugin(ISchoolToolTraverser):
    """A plugin for the pluggable traverser."""

