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
Pluggable Traverser Implementation

$Id$
"""

from zope.interface import implements
from zope.component import subscribers, queryAdapter, queryMultiAdapter
from zope.publisher.interfaces import NotFound

from schooltool.traverser import interfaces

_marker = object()

class PluggableTraverser(object):
    """Generic Pluggable Traverser."""

    implements(interfaces.IPluggableTraverser)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        # 1. Look at all the traverser plugins, whether they have an answer.
        for traverser in subscribers((self.context, request),
                                     interfaces.ITraverserPlugin):
            try:
                return traverser.publishTraverse(request, name)
            except NotFound:
                pass

        # 2. The traversers did not have an answer, so let's see whether it is
        #    a view.
        view = queryMultiAdapter((self.context, request), name=name)
        if view is not None:
            return view

        raise NotFound(self.context, name, request)


class NameTraverserPlugin(object):
    """Abstract class that traverses an object by name."""
    implements(interfaces.ITraverserPlugin)

    traversalName = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == self.traversalName:
            return self._traverse(request, name)
        raise NotFound(self.context, name, request)

    def _traverse(self, request, name):
        raise NotImplemented, 'Method must be implemented by subclasses.'


class NullTraverserPluginTemplate(NameTraverserPlugin):
    """Traverse to an adapter by name."""

    def _traverse(self, request, name):
        return self.context


def NullTraverserPlugin(traversalName):
    return type('NullTraverserPlugin', (NullTraverserPluginTemplate,),
                {'traversalName': traversalName})


class SingleAttributeTraverserPluginTemplate(NameTraverserPlugin):
    """Allow only a single attribute to be traversed."""

    def _traverse(self, request, name):
        return getattr(self.context, name)


def SingleAttributeTraverserPlugin(name):
    return type('SingleAttributeTraverserPlugin',
                (SingleAttributeTraverserPluginTemplate,),
                {'traversalName': name})


class AdapterTraverserPluginTemplate(NameTraverserPlugin):
    """Traverse to an adapter by name."""
    interface = None
    adapterName = ''

    def _traverse(self, request, name):
        adapter = queryAdapter(self.context, self.interface,
                               name=self.adapterName)
        if adapter is None:
            raise NotFound(self.context, name, request)

        return adapter


def AdapterTraverserPlugin(traversalName, interface, adapterName=''):
    return type('AdapterTraverserPlugin',
                (AdapterTraverserPluginTemplate,),
                {'traversalName': traversalName,
                 'adapterName': adapterName,
                 'interface': interface})


class ContainerTraverserPlugin(object):
    """A traverser that knows how to look up objects by name in a container."""

    implements(interfaces.ITraverserPlugin)

    def __init__(self, container, request):
        self.context = container
        self.request = request

    def publishTraverse(self, request, name):
        """See zope.publisher.interfaces.IPublishTraverse"""
        subob = self.context.get(name, None)
        if subob is None:
            raise NotFound(self.context, name, request)

        return subob


class AttributeTraverserPlugin(object):
    """A simple traverser plugin that traverses an attribute by name"""

    implements(interfaces.ITraverserPlugin)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        try:
            obj = getattr(self.context, name)
        except AttributeError:
            raise NotFound(self.context, name, request)
        else:
            return obj
