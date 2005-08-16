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
from zope.component import subscribers, queryAdapter, queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces import IPublishTraverse

from schoolbell.app.traverser.interfaces import ITraverserPlugin
from schoolbell.app.traverser.interfaces import IPluggableTraverser


class PluggableTraverser(object):
    """Generic Pluggable Traverser."""

    implements(ITraverserPlugin)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        # 1. Look at all the traverser plugins, whether they have an answer.
        for traverser in subscribers((self.context, request), ITraverserPlugin):
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


class AttributeTraverserPlugin(object):
    """A simple traverser plugin that traverses an attribute by name"""

    implements(ITraverserPlugin)

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


class SingleAttributeTraverserPluginTemplate(object):
    """Allow only a single attribute to be traversed."""

    implements(ITraverserPlugin)

    variableName = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == self.variableName:
            return getattr(self.context, name)

        raise NotFound(self.context, name, request)


def SingleAttributeTraverserPlugin(name):
    return type('SingleAttributeTraverserPlugin',
                (SingleAttributeTraverserPluginTemplate,),
                {'variableName': name})


class AdapterTraverserPluginTemplate(object):
    """Traverse to an adapter by name."""

    implements(ITraverserPlugin)

    traversalName = None
    interface = None
    adapterName = ''

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        if name == self.traversalName:
            adapter = queryAdapter(self.context, self.interface,
                                   name=self.adapterName)
            if adapter is not None:
                return adapter
        raise NotFound(self.context, name, request)


def AdapterTraverserPlugin(traversalName, interface, adapterName=''):
    return type('AdapterTraverserPlugin',
                (AdapterTraverserPluginTemplate,),
                {'traversalName': traversalName,
                 'adapterName': adapterName, 'interface': interface})


class ContainerTraverserPlugin(object):
    """A traverser that knows how to look up objects by name in a container."""

    implements(ITraverserPlugin)

    def __init__(self, container, request):
        self.context = container
        self.request = request

    def publishTraverse(self, request, name):
        """See zope.publisher.interfaces.IPublishTraverse"""
        subob = self.context.get(name, None)
        if subob is None:
            raise NotFound(self.context, name, request)

        return subob
