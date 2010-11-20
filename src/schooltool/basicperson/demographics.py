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
Demographics fields and storage
"""
from persistent.dict import PersistentDict
from persistent import Persistent

from zope.schema._field import Choice
from zope.schema._field import Date
from zope.schema import TextLine, Bool
from zope.location.location import Location
from zope.location.location import locate
from zope.interface import Interface
from zope.interface import implements
from zope.interface import implementer
from zope.component import adapts
from zope.component import adapter
from zope.container.btree import BTreeContainer
from zope.container.ordered import OrderedContainer
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm

from z3c.form import field

from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.interfaces import IEnumFieldDescription
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.interfaces import IFieldDescription


class IDemographicsForm(Interface):
    """Interface for fields that are supposed to get stored in person demographics."""


class PersonDemographicsDataContainer(BTreeContainer):
    """Storage for demographics information for all persons."""


class InvalidKeyError(Exception):
    """Key is not in demographics fields."""


class PersonDemographicsData(PersistentDict):
    """Storage for demographics information for a person."""

    def isValidKey(self, key):
        app = ISchoolToolApplication(None)
        demographics_fields = IDemographicsFields(app)
        return key in demographics_fields

    def __repr__(self):
        return '%s: %s' % (
            object.__repr__(self),
            super(PersonDemographicsData, self).__repr__())

    def __setitem__(self, key, v):
        if not self.isValidKey(key):
            raise InvalidKeyError(key)
        super(PersonDemographicsData, self).__setitem__(key, v)

    def __getitem__(self, key):
        if key not in self and self.isValidKey(key):
            self[key] = None
        return super(PersonDemographicsData, self).__getitem__(key)


@adapter(IBasicPerson)
@implementer(IDemographics)
def getPersonDemographics(person):
    app = ISchoolToolApplication(None)
    pdc = app['schooltool.basicperson.demographics_data']
    demographics = pdc.get(person.username, None)
    if demographics is None:
        pdc[person.username] = demographics = PersonDemographicsData()
    return demographics


class DemographicsFormAdapter(object):
    implements(IDemographicsForm)
    adapts(IBasicPerson)

    def __init__(self, context):
        self.__dict__['context'] = context
        self.__dict__['demographics'] = IDemographics(self.context)

    def __setattr__(self, name, value):
        self.demographics[name] = value

    def __getattr__(self, name):
        return self.demographics.get(name, None)


class DemographicsFields(OrderedContainer):
    implements(IDemographicsFields)

    def filter_key(self, key):
        """Return the subset of fields whose limited_keys list is either
           empty, or it contains the key passed."""
        result = []
        for field in self.values():
            if not field.limit_keys or key in field.limit_keys:
                result.append(field)
        return result


def setUpDefaultDemographics(app):
    dfs = DemographicsFields()
    app['schooltool.basicperson.demographics_fields'] = dfs
    locate(dfs, app, 'schooltool.basicperson.demographics_fields')
    dfs['ID'] = TextFieldDescription('ID', 'ID')
    dfs['ethnicity'] = EnumFieldDescription('ethnicity', 'Ethnicity')
    dfs['ethnicity'].items = [u'American Indian or Alaska Native',
                              u'Asian',
                              u'Black or African American',
                              u'Native Hawaiian or Other Pacific Islander',
                              u'White']
    dfs['language'] = TextFieldDescription('language', 'Language')
    dfs['placeofbirth'] = TextFieldDescription('placeofbirth', 'Place of birth')
    dfs['citizenship'] = TextFieldDescription('citizenship', 'Citizenship')


class DemographicsAppStartup(StartUpBase):
    def __call__(self):
        if 'schooltool.basicperson.demographics_fields' not in self.app:
            setUpDefaultDemographics(self.app)
        if 'schooltool.basicperson.demographics_data' not in self.app:
            self.app['schooltool.basicperson.demographics_data'] = PersonDemographicsDataContainer()


class DemographicsInit(InitBase):
    def __call__(self):
        setUpDefaultDemographics(self.app)
        self.app['schooltool.basicperson.demographics_data'] = PersonDemographicsDataContainer()


@implementer(IDemographicsFields)
@adapter(ISchoolToolApplication)
def getDemographicsFields(app):
    return app['schooltool.basicperson.demographics_fields']


class FieldDescription(Persistent, Location):
    implements(IFieldDescription)
    limit_keys = []

    def __init__(self, name, title, required=False, limit_keys=[]):
        self.name, self.title, self.required, self.limit_keys = (name,
            title, required, limit_keys)

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
    implements(IEnumFieldDescription)

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

