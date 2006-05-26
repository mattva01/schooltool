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

from zope.interface import Interface, implements
from zope import schema
from zope.schema.interfaces import IIterableSource

from schooltool import SchoolToolMessage as _

class INameInfo(Interface):

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
        required=False,
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

class SourceList(list):
    implements(IIterableSource)
    
class IDemographics(Interface):
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
        source=SourceList(['foo', 'bar']),
        required=False,
        )

    primary_language = schema.Choice(
        title=_(u"Primary language"),
        source=SourceList(['qux', 'hoi']),
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

class ISchoolData(Interface):
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
        source=SourceList(['alpha', 'beta']),
        required=False,
        )

    team = schema.Choice(
        title=_(u"Team"),
        source=SourceList(['gamma', 'delta']),
        required=False,
        )

    health_information = schema.Text(
        title=_(u"Health information"),
        required=False,
        )

class IContactInfo(Interface):
    name = schema.TextLine(
        title=_(u"Name"),
        required=False,
        )

    relationship_to_student = schema.Choice(
        title=_(u"Relationship to student"),
        source=SourceList(['parent', 'guardian', 'grandparent']),
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

    fulltext = schema.TextLine(
        title=_(u"Text"),
        required=False,
        )

    parentName = schema.TextLine(
        title=_(u"Name of parent"),
        required=False,
        )
    
    studentId = schema.TextLine(
        title=_(u"Student ID"),
        required=False,
        )

    
