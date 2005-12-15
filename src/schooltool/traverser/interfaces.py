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
Pluggable Traverser Interfaces

This implementation is independent of the presentation type. Sub-interfaces
must be written for every specific presentation type.

$Id$
"""

from zope.publisher.interfaces import IPublishTraverse


class IPluggableTraverser(IPublishTraverse):
    """A pluggable traverser.

    This traverser traverses a name by utilizing helper traversers that are
    registered as ``ITraverserPlugin`` subscribers.
    """


class ITraverserPlugin(IPublishTraverse):
    """A plugin for the pluggable traverser."""
