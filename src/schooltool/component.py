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
The schooltool component.

$Id$
"""
from zope.interface import moduleProvides
from schooltool.interfaces import IContainmentAPI, IFacetAPI
from schooltool.interfaces import ILocation, IContainmentRoot, IFaceted
from schooltool.interfaces import ComponentLookupError

moduleProvides(IContainmentAPI, IFacetAPI)

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


#
# IContainmentAPI
#

def getPath(obj):
    """Returns the path of an object implementing ILocation"""

    if IContainmentRoot.isImplementedBy(obj):
        return '/'
    cur = obj
    segments = []
    while True:
        if IContainmentRoot.isImplementedBy(cur):
            segments.append('')
            segments.reverse()
            return '/'.join(segments)
        elif ILocation.isImplementedBy(cur):
            segments.append(cur.__name__)
            cur = cur.__parent__
        else:
            raise TypeError("Cannot determine path for %s" % obj)


#
# IFacetAPI
#

def setFacet(ob, key, facet):
    """Set a facet marked with a key on a faceted object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    ob.__facets__[key] = facet

def getFacet(ob, key):
    """Get a facet of an object"""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    return ob.__facets__[key]

def queryFacet(ob, key, default=None):
    """Get a facet of an object, return the default value if there is
    none.
    """
    try:
        return getFacet(ob, key)
    except KeyError:
        return default

def getFacetItems(ob):
    """Returns a sequence of (key, facet) for all facets of an object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    return ob.__facets__.items()

