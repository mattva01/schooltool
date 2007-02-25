#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Registration of types of resources.

$Id$
"""
from zope.interface import implements
from zope.component import adapts
from zope.component import queryUtility

from schooltool import SchoolToolMessage as _
from schooltool.resource.interfaces import (IResource, IResourceFactoryUtility,
                                            ILocation, IEquipment,
                                            IResourceTypeInformation)


class ResourceFactoryUtility(object):
    implements(IResourceFactoryUtility)

    title = _("Resource")

    def columns(self):
        return []


class LocationFactoryUtility(ResourceFactoryUtility):
    implements(IResourceFactoryUtility)

    title = _("Location")


class EquipmentFactoryUtility(ResourceFactoryUtility):
    implements(IResourceFactoryUtility)

    title = _("Equipment")


class ResourceTypeAdapter(object):
    implements(IResourceTypeInformation)
    adapts(IResource)

    id = "resource"

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        queryUtility(IResourceFactoryUtility, name=self.id)


class LocationTypeAdapter(ResourceTypeAdapter):
    adapts(ILocation)

    id = "location"


class EquipmentTypeAdapter(ResourceTypeAdapter):
    adapts(IEquipment)

    id = "equipment"
