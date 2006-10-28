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

from zope.interface import Interface, implements, Attribute
from zope import schema
from zope.schema.interfaces import IIterableSource

from schooltool.app.app import ISchoolToolApplication
from schooltool import SchoolToolMessage as _
from schooltool.person.interfaces import IPerson

class IDemographicsPerson(IPerson):
    nameinfo = Attribute('Name info')
    demographics = Attribute('Demographics')
    schooldata = Attribute('School data')
    parent1 = Attribute('Parental contact')
    parent2 = Attribute('Parental contact')
    emergency1 = Attribute('Emergency contact')
    emergency2 = Attribute('Emergency contact')
    emergency3 = Attribute('Emergency contact')

class INameInfo(Interface):
    """Name information for a person.
    """

    prefix = schema.TextLine(
        title=_(u"Prefix"),
        description=_(u"Prefix such as Mr., Mrs."),
        required=False,
        )

    first_name = schema.TextLine(
        title=_(u"First name"),
        required=False,
        )

    middle_name = schema.TextLine(
        title=_(u"Middle name"),
        required=False,
        )

    last_name = schema.TextLine(
        title=_(u"Last name"),
        required=True,
        )

    suffix = schema.TextLine(
        title=_(u"Suffix"),
        required=False,
        )

    preferred_name = schema.TextLine(
        title=_(u"Preferred name"),
        description=_(u"Name by which the student prefers to be called"),
        required=False,
        )

    full_name = schema.TextLine(
        title=_(u"Full name"),
        required=True,
        )

    photo = schema.Bytes(
        title=_("Photo"),
        required=False,
        description=_("""Photo (in JPEG format)"""),
        )

class SourceList(list):
    """A simple list-based source for Choice fields.
    """
    implements(IIterableSource)


ethnicitySource = SourceList([
    'American Indian or Alaska Native',
    'Asian',
    'Black or African American',
    'Native Hawaiian or Other Pacific Islander',
    'White'])


languageSource = SourceList([
    'English',
    'Spanish',
    'Chinese',
    'German',
    'Tagalog',
    'Vietnamese',
    'Italian',
    'Korean',
    'Russian',
    'Polish',
    'Arabic',
    ])


class IDemographics(Interface):
    """Demographical information about a person.
    """

    # XXX how to translate male and female? in widget?
    gender = schema.Choice(
        title=_(u"Gender"),
        source=SourceList(['male', 'female']),
        required=False,
        )

    birth_date = schema.Date(
        title=_(u"Birth date"),
        required=False,
        )

    ethnicity = schema.Choice(
        title=_(u"Ethnicity"),
        source=ethnicitySource,
        required=False,
        )

    primary_language = schema.Choice(
        title=_(u"Primary language"),
        source=languageSource,
        required=False,
        )

    special_education = schema.Bool(
        title=_(u"Special education"),
        required=False
        )

    previous_school = schema.Text(
        title=_(u"Previous school"),
        required=False
        )


class ITeachersSource(IIterableSource):
    """A source of names of teachers.
    """

class IGroupsSource(IIterableSource):
    """A source of names of groups.
    """

class TeachersSource(object):
    implements(ITeachersSource)

    def teachers(self):
        teachers = []
        for teacher in ISchoolToolApplication(
            None)['groups']['teachers'].members:
            teachers.append(teacher.__name__)
        return teachers

    def __iter__(self):
        return iter(self.teachers())

    def __len__(self):
        return len(self.teachers())


class GroupsSource(object):
    implements(IGroupsSource)

    def __iter__(self):
        return iter(ISchoolToolApplication(None)['groups'].keys())

    def __len__(self):
        return len(ISchoolToolApplication(None)['groups'].keys())

class ISchoolData(Interface):
    """School-specific data for a person.
    """
    id = schema.TextLine(
        title=_(u"ID"),
        required=False,
        )

    enrollment_date = schema.Date(
        title=_(u"Enrollment date"),
        required=False,
        )

    projected_graduation_year = schema.Int(
        title=_(u"Projected graduation year"),
        required=False,
        )

    advisor = schema.Choice(
        title=_(u"Advisor"),
        source=TeachersSource(),
        required=False,
        )

    team = schema.Choice(
        title=_(u"Team"),
        source=GroupsSource(),
        required=False,
        )

    health_information = schema.Text(
        title=_(u"Health information"),
        required=False,
        )


relationshipToStudentSource = SourceList([
    'parent',
    'guardian',
    'grandparent',
    'step-parent',
    'friend of family',
    'other'])


class IContactInfo(Interface):
    """Contact information for a person.

    A person can have more than one contact informations at the
    same time.
    """
    name = schema.TextLine(
        title=_(u"Name"),
        required=False,
        )

    relationship_to_student = schema.Choice(
        title=_(u"Relationship to student"),
        source=relationshipToStudentSource,
        required=False,
        )

    street = schema.Text(
        title=_(u"Street"),
        required=False,
        )

    city = schema.TextLine(
        title=_(u"City"),
        required=False,
        )

    state = schema.TextLine(
        title=_(u"State"),
        required=False,
        )

    postal_code = schema.TextLine(
        title=_(u"Postal code"),
        required=False,
        )

    home_phone = schema.TextLine(
        title=_(u"Home phone"),
        required=False,
        )

    work_phone = schema.TextLine(
        title=_(u"Work phone"),
        required=False,
        )

    cell_phone = schema.TextLine(
        title=_(u"Cell phone"),
        required=False,
        )

    notes = schema.Text(
        title=_(u"Notes"),
        required=False,
        )


class ISearch(Interface):
    """Particular aspects of a person that can be indexed for search.
    """

    fulltext = schema.TextLine(
        title=_(u"Text"),
        description=_(u"Full text search in name"),
        required=False,
        )

    parentName = schema.TextLine(
        title=_(u"Name of parent"),
        description=_(u"Full text search in parent names"),
        required=False,
        )

    studentId = schema.TextLine(
        title=_(u"Student ID"),
        required=False,
        )


