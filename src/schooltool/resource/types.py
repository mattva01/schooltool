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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Registration of types of resources.
"""
from zope.component import adapts
from zope.component import queryUtility
from zope.interface import directlyProvides
from zope.interface import implements

from zc.table.column import GetterColumn
from zc.table.interfaces import ISortableColumn

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import SchoolToolMessage as _
from schooltool.resource.interfaces import (IResource, IResourceFactoryUtility,
                                            ILocation, IEquipment,
                                            IResourceTypeInformation,
                                            IResourceSubTypes)
from schooltool.table.table import LocaleAwareGetterColumn


class ResourceFactoryUtility(object):
    implements(IResourceSubTypes, IResourceFactoryUtility)

    def __init__(self):
        self.interface = IResource

    def types(self):
        app = ISchoolToolApplication(None)
        types = set()
        for resource in app['resources'].values():
            if self.interface.providedBy(resource):
                types.add(resource.type)
        return list(types)

    title = _("Resource")

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

class LocationFactoryUtility(ResourceFactoryUtility):
    implements(IResourceFactoryUtility)

    title = _("Location")

    def __init__(self):
        self.interface = ILocation

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        capacity = GetterColumn(
            name='capacity',
            title=_(u'Capacity'),
            getter=lambda i, f: i.capacity,
            subsort=True)
        directlyProvides(capacity, ISortableColumn)
        return [title, capacity]


class EquipmentFactoryUtility(ResourceFactoryUtility):
    implements(IResourceFactoryUtility)

    title = _("Equipment")

    def __init__(self):
        self.interface = IEquipment

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u'Title'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        type = GetterColumn(
            name='type',
            title=_(u'Type'),
            getter=lambda i, f: i.type,
            subsort=True)
        directlyProvides(type, ISortableColumn)
        manufacturer = GetterColumn(
            name='manufacturer',
            title=_(u'Manufacturer'),
            getter=lambda i, f: i.manufacturer,
            subsort=True)
        directlyProvides(manufacturer, ISortableColumn)
        model = GetterColumn(
            name='model',
            title=_(u'Model'),
            getter=lambda i, f: i.model,
            subsort=True)
        directlyProvides(model, ISortableColumn)
        serialNumber = GetterColumn(
            name='serialNumber',
            title=_(u'Serial Number'),
            getter=lambda i, f: i.serialNumber,
            subsort=True)
        directlyProvides(serialNumber, ISortableColumn)
        purchaseDate = GetterColumn(
            name='purchaseDate',
            title=_(u'Purchase Date'),
            getter=lambda i, f: i.purchaseDate,
            subsort=True)
        directlyProvides(purchaseDate, ISortableColumn)
        return [title, type, manufacturer, model, serialNumber, purchaseDate]


class ResourceTypeAdapter(object):
    implements(IResourceTypeInformation)
    adapts(IResource)

    id = "resource"

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        return queryUtility(IResourceFactoryUtility, name=self.id).title


class LocationTypeAdapter(ResourceTypeAdapter):
    adapts(ILocation)

    id = "location"


class EquipmentTypeAdapter(ResourceTypeAdapter):
    adapts(IEquipment)

    id = "equipment"
