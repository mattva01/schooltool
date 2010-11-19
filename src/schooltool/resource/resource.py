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
from persistent.dict import PersistentDict

from zope.component import adapts, adapter
from zope.interface import implements, implementer
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer
from zope.container.ordered import OrderedContainer
from zope.location.location import Location
from zope.schema import TextLine, Bool, Date, Choice
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm

from schooltool.app.app import Asset
from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.security import LeaderCrowd
from schooltool.securitypolicy.crowds import TeachersCrowd
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.resource import interfaces
from schooltool.securitypolicy.crowds import ConfigurableCrowd, AggregateCrowd
from schooltool.securitypolicy.crowds import AuthenticatedCrowd
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
        self.app[RESOURCE_DEMO_FIELDS_KEY] = DemographicsFields()
        self.app[RESOURCE_DEMO_DATA_KEY] = ResourceDemographicsDataContainer()


class ResourceStartUp(StartUpBase):

    def __call__(self):
        if RESOURCE_DEMO_FIELDS_KEY not in self.app:
            self.app[RESOURCE_DEMO_FIELDS_KEY] = DemographicsFields()
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
                LeaderCrowd, AuthenticatedCrowd, TeachersCrowd]


class ResourceCalendarEditorsCrowd(AggregateCrowd):

    adapts(interfaces.IBaseResource)
    implements(ICalendarParentCrowd)

    def crowdFactories(self):
        return [LeaderCrowd, TeachersCrowd]


###################  DemographicsFields   #################
class DemographicsFields(OrderedContainer):
    implements(interfaces.IDemographicsFields)

    def filter_resource_type(self, resource_type):
        """Return the subset of fields whose limited_resource_types list is
           either empty, or it contains the resource_type passed."""
        result = []
        for field in self.values():
            if (not field.limit_resource_types or
                resource_type in field.limit_resource_types):
                result.append(field)
        return result


@implementer(interfaces.IDemographicsFields)
@adapter(ISchoolToolApplication)
def getDemographicsFields(app):
    return app[RESOURCE_DEMO_FIELDS_KEY]


class FieldDescription(Location, Persistent):
    implements(interfaces.IFieldDescription)
    limit_resource_types = []

    def __init__(self, name, title, required=False, limit_resource_types=[]):
        self.name, self.title, self.required, self.limit_resource_types = (name,
            title, required, limit_resource_types)

    def setUpField(self, form_field):
        form_field.required = self.required
        form_field.__name__ = str(self.name)
        form_field.interface = IDemographicsForm
        return field.Fields(form_field)


# XXX: IMHO all IDNA conversions should be replaced by punycode.
#      64 max length limitation simply breaks things too often.
class IDNAVocabulary(SimpleVocabulary):

    def createTerm(cls, *args):
        """Create a single term from data.

        Encode the value using idna encoding so it would look sane in
        the form if it's ascii, but still work if it uses unicode.
        """
        value = args[0]
        token = value.encode('idna')
        title = value
        return SimpleTerm(value, token, title)
    createTerm = classmethod(createTerm)


class EnumFieldDescription(FieldDescription):
    implements(interfaces.IEnumFieldDescription)

    items = []

    def makeField(self):
        return self.setUpField(Choice(
                title=unicode(self.title),
                vocabulary=IDNAVocabulary.fromValues(self.items)
                ))


class DateFieldDescription(FieldDescription):

    def makeField(self):
        return self.setUpField(Date(title=unicode(self.title)))


class TextFieldDescription(FieldDescription):

    def makeField(self):
        return self.setUpField(TextLine(title=unicode(self.title)))


class BoolFieldDescription(FieldDescription):

    def makeField(self):
        return self.setUpField(Bool(title=unicode(self.title)))


###################  DemographicsData   #################
class ResourceDemographicsDataContainer(BTreeContainer):
    """Storage for demographics information for all resources."""


class InvalidKeyError(Exception):
    """Key is not in demographics fields."""


class ResourceDemographicsData(PersistentDict):
    """Storage for demographics information for a resource."""
    implements(interfaces.IDemographics)

    def isValidKey(self, key):
        app = ISchoolToolApplication(None)
        demographics_fields = interfaces.IDemographicsFields(app)
        return key in demographics_fields

    def __repr__(self):
        return '%s: %s' % (
            object.__repr__(self),
            super(ResourceDemographicsData, self).__repr__())

    def __setitem__(self, key, v):
        if not self.isValidKey(key):
            raise InvalidKeyError(key)
        super(ResourceDemographicsData, self).__setitem__(key, v)

    def __getitem__(self, key):
        if key not in self and self.isValidKey(key):
            self[key] = None
        return super(ResourceDemographicsData, self).__getitem__(key)


@adapter(interfaces.IResource)
@implementer(interfaces.IDemographics)
def getResourceDemographics(resource):
    app = ISchoolToolApplication(None)
    rdc = app[RESOURCE_DEMO_DATA_KEY]
    demographics = rdc.get(resource.__name__, None)
    if demographics is None:
        rdc[resource.__name__] = demographics = ResourceDemographicsData()
    return demographics

