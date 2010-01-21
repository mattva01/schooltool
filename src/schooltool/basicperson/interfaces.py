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
SchoolTool basic person interfaces.
"""
from zope.container.interfaces import IContainer
from zope.container.interfaces import IOrderedContainer
from zope.schema import Date, Choice, TextLine, Bool
from zope.configuration.fields import PythonIdentifier
from zope.interface import Interface, Attribute

from zope.schema import List
from zope.schema.interfaces import IIterableSource

from schooltool.common import SchoolToolMessage as _


class IBasicPerson(Interface):
    """Marker interface for Lyceum specific person."""

    prefix = TextLine(
        title=_(u"Prefix"),
        required=False,
        )

    first_name = TextLine(
        title=_(u"First name"),
        required=True,
        )

    middle_name = TextLine(
        title=_(u"Middle name"),
        required=False,
        )

    last_name = TextLine(
        title=_(u"Last name"),
        required=True,
        )

    suffix = TextLine(
        title=_(u"Suffix"),
        required=False,
        )

    preferred_name = TextLine(
        title=_(u"Preferred name"),
        required=False,
        )

    gender = Choice(
        title=_(u"Gender"),
        values=[_('male'), _('female')],
        required=False,
        )

    birth_date = Date(
        title=_(u"Birth date"),
        description=_(u"(yyyy-mm-dd)"),
        required=False,
        )

    advisors = Attribute("""Advisors of the person""")

    advisees = Attribute("""Advisees of the person""")


class IBasicPersonSource(IIterableSource):
    """Marker interface for sources that list basic persons."""


# XXX should be in skin or common, or more properly - core
class IGroupSource(IIterableSource):
    """Marker interface for sources that list schooltool groups."""


class IAdvisor(Interface):

    students = Attribute("""Students being advised by the advisor.""")


    def addStudent(student):
        """Add a student to the advised students list."""

    def removeStudent(student):
        """Remove this student from the advised students list."""


class IDemographics(IContainer):
    """Demographics data storage for a person.

    Stores any kind of data defined by field descriptions that are set
    up for the person container.
    """


class IDemographicsFields(IOrderedContainer):
    """Demographics field storage."""


class IFieldDescription(Interface):
    """Demographics field."""

    title = TextLine(
        title = _(u"Title"),
        description = _(u"The title of this Field Description"))

    name = PythonIdentifier(
        title = _(u"ID"),
        description = _(u"Unique ID of this Field Description"))

    required = Bool(
        title = _(u"Required"),
        description = _(u"Whether this Field is required or not"))


class IEnumFieldDescription(IFieldDescription):
    """Enumeration demographics field."""

    items = List(
        title = _('List of values'))
