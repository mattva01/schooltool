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
SchoolBell application object

$Id: app.py 4704 2005-08-15 13:22:06Z srichter $
"""
__docformat__ = 'restructuredtext'
from persistent import Persistent

from zope.interface import implements
from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import btree
from zope.app.container.contained import Contained

from schooltool.resource import interfaces


class ResourceContainer(btree.BTreeContainer):
    """Container of resources."""

    implements(interfaces.IResourceContainer, IAttributeAnnotatable)


class Resource(Persistent, Contained):
    """Resource."""

    implements(interfaces.IResourceContained, IAttributeAnnotatable)

    # BBB: ...
    isLocation = False # backwards compatibility

    def __init__(self, title=None, description=None, isLocation=False):
        self.title = title
        self.description = description
        self.isLocation = isLocation


def addResourceContainerToApplication(event):
    event.object['resources'] = ResourceContainer()
