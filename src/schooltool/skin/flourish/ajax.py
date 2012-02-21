#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Schooltool page AJAX parts.
"""

import zope.security.proxy
from zope.component import adapts, queryMultiAdapter
from zope.interface import implements
from zope.location.interfaces import LocationError
from zope.publisher.interfaces import NotFound
from zope.traversing.interfaces import ITraversable

from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManagerBase
from schooltool.skin.flourish.viewlet import ManagerViewlet
from schooltool.traverser.traverser import TraverserPlugin


class AJAXPart(Viewlet):
    implements(interfaces.IAJAXPart)

    fromPublication = False

    @property
    def ignoreRequest(self):
        return not self.fromPublication


class CompositeAJAXPart(ManagerViewlet):
    implements(interfaces.IAJAXPart)

    fromPublication = False

    @property
    def ignoreRequest(self):
        return not self.fromPublication


class AJAXParts(ViewletManagerBase):
    implements(interfaces.IAJAXParts)

    fromPublication = False
    render = lambda self, *args, **kw: ''

    def collect(self):
        ViewletManagerBase.collect(self)
        for viewlet in self.cache.values():
            unproxied = zope.security.proxy.removeSecurityProxy(viewlet)
            unproxied.fromPublication = self.fromPublication

    def publishTraverse(self, request, name):
        part = self.get(name)
        if part is None:
            raise NotFound(self, name, request)
        return part


class AJAXPartsTraversable(object):
    adapts(AJAXParts)
    implements(ITraversable)

    def __init__(self, parts):
        self.parts = parts

    def traverse(self, name, furtherPath):
        __traceback_info__ = (self.parts, name, furtherPath)
        try:
            return self.parts[name]
        except (KeyError, TypeError):
            raise LocationError(self.parts, name)


class ViewAJAXPartsTraverser(TraverserPlugin):

    def __init__(self, view, request):
        self.view = view
        self.context = view.context
        self.request = request

    def traverse(self, name):
        parts = queryMultiAdapter(
            (self.context, self.request, self.view),
            interfaces.IContentProvider, 'ajax')
        if parts is None:
            raise NotFound(self.view, name, self.request)
        parts.fromPublication = True
        return parts
