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
SchoolTool resource object
"""
__docformat__ = 'restructuredtext'

from persistent import Persistent

from zope.component import adapts, adapter
from zope.interface import implements, implementer
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer

from schooltool.app.app import Asset
from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.utils import vocabulary
from schooltool.app.security import LeaderCrowd
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.demographics import PersonDemographicsData
from schooltool.basicperson.demographics import DemographicsFields
from schooltool.basicperson.demographics import IDemographicsForm
from schooltool.basicperson.interfaces import IFieldFilterVocabulary
from schooltool.resource import interfaces
from schooltool.securitypolicy.crowds import TeachersCrowd
from schooltool.securitypolicy.crowds import ConfigurableCrowd, AggregateCrowd
from schooltool.securitypolicy.crowds import AdministratorsCrowd
from schooltool.securitypolicy.crowds import ManagersCrowd, ClerksCrowd
from schooltool.common import SchoolToolMessage as _


RESOURCE_DEMO_FIELDS_KEY = 'schooltool.resource.demographics_fields'
RESOURCE_DEMO_DATA_KEY = 'schooltool.resource.demographics_data'


class ResourceContainer(BTreeContainer):
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
        self.app[RESOURCE_DEMO_FIELDS_KEY] = ResourceDemographicsFields()
        self.app[RESOURCE_DEMO_DATA_KEY] = ResourceDemographicsDataContainer()


class ResourceStartUp(StartUpBase):

    def __call__(self):
        if RESOURCE_DEMO_FIELDS_KEY not in self.app:
            self.app[RESOURCE_DEMO_FIELDS_KEY] = ResourceDemographicsFields()
        if RESOURCE_DEMO_DATA_KEY not in self.app:
            self.app[RESOURCE_DEMO_DATA_KEY] = \
                ResourceDemographicsDataContainer()


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
                AdministratorsCrowd, ManagersCrowd, ClerksCrowd,
                LeaderCrowd, TeachersCrowd]


class ResourceCalendarEditorsCrowd(AggregateCrowd):

    adapts(interfaces.IBaseResource)
    implements(ICalendarParentCrowd)

    def crowdFactories(self):
        return [ManagersCrowd, ClerksCrowd,
                LeaderCrowd, TeachersCrowd]


###################  Demographics   #################
class ResourceDemographicsFields(DemographicsFields):
    """Storage for demographics fields for all resources."""
    implements(interfaces.IResourceDemographicsFields)


@implementer(interfaces.IResourceDemographicsFields)
@adapter(ISchoolToolApplication)
def getResourceDemographicsFields(app):
    return app[RESOURCE_DEMO_FIELDS_KEY]


class ResourceDemographicsDataContainer(BTreeContainer):
    """Storage for demographics information for all resources."""


class ResourceDemographicsData(PersonDemographicsData):
    """Storage for demographics information for a resource."""
    implements(interfaces.IResourceDemographics)

    def isValidKey(self, key):
        app = ISchoolToolApplication(None)
        demographics_fields = interfaces.IResourceDemographicsFields(app)
        return key in demographics_fields


@adapter(interfaces.IBaseResource)
@implementer(interfaces.IResourceDemographics)
def getResourceDemographics(resource):
    app = ISchoolToolApplication(None)
    rdc = app[RESOURCE_DEMO_DATA_KEY]
    demographics = rdc.get(resource.__name__, None)
    if demographics is None:
        rdc[resource.__name__] = demographics = ResourceDemographicsData()
    return demographics


class DemographicsFormAdapter(object):
    implements(IDemographicsForm)
    adapts(interfaces.IBaseResource)

    def __init__(self, context):
        self.__dict__['context'] = context
        self.__dict__['demographics'] = interfaces.IResourceDemographics(
            self.context)

    def __setattr__(self, name, value):
        self.demographics[name] = value

    def __getattr__(self, name):
        return self.demographics.get(name, None)


@adapter(interfaces.IResourceDemographicsFields)
@implementer(IFieldFilterVocabulary)
def getLimitKeyVocabularyForResourceFields(resource_field_description_container):
     return vocabulary([
        ('resource', _('Resource')),
        ('location', _('Location')),
        ('equipment', _('Equipment')),
        ])
