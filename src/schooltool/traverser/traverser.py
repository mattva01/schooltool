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
Pluggable Traverser Implementation
"""

from zope.interface import implements
from zope.component import queryAdapter, queryMultiAdapter
from zope.publisher.interfaces import NotFound

from schooltool.traverser import interfaces


class Traverser(object):
    """A sipmple traverser base."""
    implements(interfaces.IPluggableTraverser)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        return self.traverse(name)

    def traverse(self, name):
        raise NotFound(self.context, name, self.request)


class PluggableTraverser(object):
    """Generic Pluggable Traverser."""

    implements(interfaces.IPluggableTraverser)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        # 1. Look for a named traverser plugin.
        named_traverser = queryMultiAdapter((self.context, request),
                                            interfaces.ITraverserPlugin,
                                            name=name)
        if named_traverser is not None:
            try:
                return named_traverser.traverse(name)
            except NotFound:
                pass

        # 2. Named traverser plugin was of no use, let's try a generic one.
        traverser = queryMultiAdapter((self.context, request),
                                      interfaces.ITraverserPlugin)
        if traverser is not None:
            try:
                return traverser.traverse(name)
            except NotFound:
                pass

        # 3. The traversers did not have an answer, so let's see whether it is
        #    a view.
        view = queryMultiAdapter((self.context, request), name=name)
        if view is not None:
            return view

        raise NotFound(self.context, name, request)

    def browserDefault(self, request):
        return self.context, ('index.html', )


class TraverserPlugin(object):
    implements(interfaces.ITraverserPlugin)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def traverse(self, name):
        raise NotFound(self.context, name, self.request)


class NullTraverserPlugin(TraverserPlugin):
    """Traverse to the context itself (i.e. nowhere)."""

    def traverse(self, name):
        return self.context


class AttributeTraverserPlugin(TraverserPlugin):
    """Traverse to attributes of the context."""

    def traverse(self, name):
        try:
            obj = getattr(self.context, name)
        except AttributeError:
            raise NotFound(self.context, name, self.request)
        else:
            return obj


class AdapterTraverserPlugin(TraverserPlugin):
    """Traverse to an adapter by name."""
    interface = None
    adapterName = ''

    def traverse(self, name):
        adapter = queryAdapter(self.context, self.interface,
                               name=self.adapterName)
        if adapter is None:
            raise NotFound(self.context, name, self.request)

        return adapter


class ContainerTraverserPlugin(TraverserPlugin):
    """A traverser that knows how to look up objects by name in a container."""

    def traverse(self, name):
        subob = self.context.get(name, None)
        if subob is None:
            raise NotFound(self.context, name, self.request)
        return subob
