#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
SchoolTool traverser metadirectives.
"""
from zope.security.zcml import Permission
from zope.schema import TextLine
from zope.interface import Interface
from zope.configuration.fields import GlobalObject, GlobalInterface


class ITraverser(Interface):
    for_ = GlobalInterface(
        title=u"The interface this traverser is for.",
        required=True,
        )

    type = GlobalInterface(
        title=u"Request type",
        required=True,
        )

    factory = GlobalObject(
        title=u"The pluggable traverser implementation.",
        required=True,
        )

    permission = Permission(
        title=u"Permission",
        description=u"The permission needed to use the view.",
        required=False,
        )

    provides = GlobalInterface(
        title=u"Interface the component provides",
        required=False,
        )


class IPluggableTraverser(ITraverser):

    factory = GlobalObject(
        title=u"The pluggable traverser implementation.",
        required=False,
        )


class ITraverserPluginBase(Interface):

    for_ = GlobalObject(
        title=u"The interface this plugin is for.",
        required=True,
        )

    layer = GlobalObject(
        title=u"The layer the plugin is declared for",
        required=False,
        )

    name = TextLine(
        title=u"The name the traverser will be traversing into.",
        required=False,
        )

    permission = Permission(
        title=u"Permission",
        required=False,
        )


class ITraverserPlugin(ITraverserPluginBase):
    """Traverser plugin zcml directive."""

    plugin = GlobalObject(
        title=u"The plugin that does the traversal.",
        required=True,
        )


class INamedTraverserPlugin(ITraverserPluginBase):
    """A simple safeguard against rogue generic traversers.

    Make traversal name mandatory.
    """
    name = TextLine(
        title=u"The name the traverser will be traversing into.",
        required=True,
        )


class INullTraverserPlugin(INamedTraverserPlugin):
    """Null traverser plugin zcml directive.

    The traverser returns the context.
    """


class IAttributeTraverserPlugin(INamedTraverserPlugin):
    """Attribute traverser plugin zcml directive.

    Traverses to an attribute of the context.
    """


class IAdapterTraverserPlugin(INamedTraverserPlugin):
    """Adapter traverser plugin zcml directive.

    Adapts context to the given interface.
    """

    adapter = GlobalObject(
        title=u"The interface this plugin will be adapting to.",
        required=True,
        )

    adapter_name = TextLine(
        title=u"Adapter name to use when adapting to given interface.",
        required=False,
        )
