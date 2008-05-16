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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool traverser metaconfiguration code.

$Id$

"""
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.component.zcml import adapter as handle_adapter

from schooltool.traverser.traverser import NullTraverserPlugin
from schooltool.traverser.traverser import SingleAttributeTraverserPlugin
from schooltool.traverser.traverser import AdapterTraverserPlugin
from schooltool.traverser.interfaces import ITraverserPlugin


def adapterTraverserPlugin(_context, for_, name, adapter,
                           layer=IDefaultBrowserLayer,
                           permission=None):
    factory = AdapterTraverserPlugin(name, adapter)
    handle_adapter(_context, [factory],
                   provides=ITraverserPlugin,
                   for_=(for_, layer),
                   permission=permission,
                   name=name)


def singleAttributeTraverserPlugin(_context, for_, name,
                           layer=IDefaultBrowserLayer,
                           permission=None):
    factory = SingleAttributeTraverserPlugin(name)
    handle_adapter(_context, [factory],
                   provides=ITraverserPlugin,
                   for_=(for_, layer),
                   permission=permission,
                   name=name)


def nullTraverserPlugin(_context, for_, name,
                           layer=IDefaultBrowserLayer,
                           permission=None):
    factory = NullTraverserPlugin(name)
    handle_adapter(_context, [factory],
                   provides=ITraverserPlugin,
                   for_=(for_, layer),
                   permission=permission,
                   name=name)
