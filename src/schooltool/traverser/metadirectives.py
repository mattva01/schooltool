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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool traverser metadirectives.

$Id$

"""
from zope.app.component.back35 import LayerField
from zope.security.zcml import Permission
from zope.schema import TextLine
from zope.interface import Interface
from zope.configuration.fields import GlobalObject


class ITraverserPluginDirective(Interface):

    name = TextLine(
        title=u"The name the tracerser will be traversing into.",
        required=True
        )

    for_ = GlobalObject(
        title=u"The interface this plugin is for.",
        required=True
        )

    layer = LayerField(
        title=u"The layer the plugin is declared for",
        required=False
        )

    permission = Permission(
        title=u"Permission",
        required=False,
        )


class IAdapterTraverserPlugin(ITraverserPluginDirective):
    """Adapter traverser plugin zcml directive."""

    adapter = GlobalObject(
        title=u"The interface this plugin will be adapting to.",
        required=True
        )


class ISingleAttributeTraverserPlugin(ITraverserPluginDirective):
    """Single attribute traverser plugin zcml directive."""


class INullTraverserPlugin(ITraverserPluginDirective):
    """Null traverser plugin zcml directive."""
