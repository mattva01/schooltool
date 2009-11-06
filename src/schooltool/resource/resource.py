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
SchoolTool resource object

$Id$
"""
__docformat__ = 'restructuredtext'
from persistent import Persistent

from zope.component import adapts
from zope.interface import implements
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import btree
from zope.app.container.contained import Contained

from schooltool.app.app import Asset
from schooltool.app.app import InitBase
from schooltool.app.security import LeaderCrowd
from schooltool.securitypolicy.crowds import TeachersCrowd
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.resource import interfaces
from schooltool.securitypolicy.crowds import ConfigurableCrowd, AggregateCrowd
from schooltool.securitypolicy.crowds import AuthenticatedCrowd
from schooltool.common import SchoolToolMessage as _


class ResourceContainer(btree.BTreeContainer):
    """Container of resources."""

    implements(interfaces.IResourceContainer, IAttributeAnnotatable)


class BaseResource(Persistent, Contained, Asset):
    """Base Resource."""

    implements(interfaces.IBaseResource, IAttributeAnnotatable)

    type = _(u"Resource")

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description
        self.notes = u""


class Resource(BaseResource):
    """Resource."""

    implements(interfaces.IResource)

    # BBB so that evolution scripts would work
    isLocation = None


class Location(BaseResource):
    """Location."""

    implements(interfaces.ILocation)

    capacity = None


class Equipment(BaseResource):
    """Equipment."""

    implements(interfaces.IEquipment)

    type = u""
    manufacturer = u""
    model = u""
    serialNumber = u""
    purchaseDate = None


class ResourceInit(InitBase):

    def __call__(self):
        self.app['resources'] = ResourceContainer()


class ResourceViewersCrowd(ConfigurableCrowd):

    setting_key = 'everyone_can_view_resource_info'


class ResourceContainerViewersCrowd(ConfigurableCrowd):

    setting_key = 'everyone_can_view_resource_list'


class ResourceCalendarViewersSettingCrowd(ConfigurableCrowd):

    setting_key = "everyone_can_view_resource_calendar"


class ResourceCalendarViewersCrowd(AggregateCrowd):

    adapts(interfaces.IBaseResource)
    implements(ICalendarParentCrowd)

    def crowdFactories(self):
        return [ResourceCalendarViewersSettingCrowd,
                LeaderCrowd, AuthenticatedCrowd, TeachersCrowd]


class ResourceCalendarEditorsCrowd(AggregateCrowd):

    adapts(interfaces.IBaseResource)
    implements(ICalendarParentCrowd)

    def crowdFactories(self):
        return [LeaderCrowd, TeachersCrowd]
