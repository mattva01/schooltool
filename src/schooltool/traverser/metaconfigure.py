#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
SchoolTool traverser metaconfiguration code.
"""
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces import IPublishTraverse
from zope.component.zcml import adapter as handle_adapter
from zope.component.zcml import view

from schooltool.traverser.traverser import PluggableTraverser
from schooltool.traverser.traverser import NullTraverserPlugin
from schooltool.traverser.traverser import AttributeTraverserPlugin
from schooltool.traverser.traverser import AdapterTraverserPlugin
from schooltool.traverser.interfaces import ITraverserPlugin


def traverser(_context, for_, type, factory,
              provides=IPublishTraverse,
              permission=None):
    view(_context, [factory], type, '', [for_],
         permission=permission,
         allowed_interface=None, allowed_attributes=None,
         provides=provides)


def pluggableTraverser(_context, for_, type,
                       factory=PluggableTraverser,
                       provides=IPublishTraverse,
                       permission=None):
    view(_context, [factory], type, '', [for_],
         permission=permission,
         allowed_interface=None, allowed_attributes=None,
         provides=provides)


def traverserPlugin(_context, for_, plugin,
                    name='',
                    layer=IDefaultBrowserLayer,
                    permission=None):
    plugin = type(plugin.__name__, (plugin, ), {'__name__': name})
    handle_adapter(_context, [plugin],
                   provides=ITraverserPlugin,
                   for_=(for_, layer),
                   permission=permission,
                   name=name)


def nullTraverserPlugin(_context, for_, name,
                        layer=IDefaultBrowserLayer,
                        permission=None):
    traverserPlugin(
        _context, for_, NullTraverserPlugin,
        name=name, layer=layer, permission=permission)


def attributeTraverserPlugin(_context, for_, name,
                             layer=IDefaultBrowserLayer,
                             permission=None):
    traverserPlugin(
        _context, for_, AttributeTraverserPlugin,
        name=name, layer=layer, permission=permission)


def adapterTraverserPlugin(_context, for_, name, adapter,
                           adapter_name='',
                           layer=IDefaultBrowserLayer,
                           permission=None):
    plugin = type('%sAdapterTraverserPlugin' % adapter.__name__,
                  (AdapterTraverserPlugin,),
                  {'adapterName': adapter_name,
                   'interface': adapter})
    traverserPlugin(_context, for_, plugin,
                    name=name, layer=layer, permission=permission)
