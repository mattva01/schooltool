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
The schooltool adapters.

$Id$
"""
from schooltool.interfaces import IPath, ILocation

adapterRegistry = {}

provideAdapter = adapterRegistry.__setitem__

def getAdapter(object, interface):
    """Stub adapter lookup.

    Only matches exact resulting interfaces and does not look at the
    context's interfaces at all.  Will be replaced with PyProtocols
    when we need more features.
    """

    if interface.isImplementedBy(object):
        return object
    try:
        factory = adapterRegistry[interface]
    except KeyError:
        raise ComponentLookupError("adapter from %s to %s"
                                   % (object, interface))
    return factory(object)

class ComponentLookupError(Exception):
    """An exception for component architecture."""

class PathAdapter:
    """Adapter from ILocation to IPath."""

    def __init__(self, context):
        self.context = context

    def path(self):
        location = getAdapter(self.context, ILocation)
        if self.context.__parent__ is None:
            raise ValueError("Cannot determine the canonical path for %s" %
                             location)
        # XXX too many adapters.  Refactor when we've got a clearer idea
        # of what is a root group.
        parentPath = getAdapter(location.__parent__, IPath).path()
        if parentPath == '/':
            parentPath = ''
        return '/'.join((parentPath, location.__name__))

provideAdapter(IPath, PathAdapter)
