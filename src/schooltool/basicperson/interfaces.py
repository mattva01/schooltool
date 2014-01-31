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
SchoolTool basic person interfaces.
"""
from zope.container.interfaces import IContainer
from zope.container.interfaces import IOrderedContainer
from zope.schema import Date, Choice, TextLine, Bool, List, Int
from zope.configuration.fields import PythonIdentifier
from zope.interface import Interface, Attribute

from zope.schema.interfaces import IVocabularyTokenized

from schooltool.app.utils import vocabulary
from schooltool.common import SchoolToolMessage as _


class IBasicPerson(Interface):
    """Marker interface for a basic person."""

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
        vocabulary=vocabulary([('male', _('Male')), ('female', _('Female')),]),
        required=False,
        )

    birth_date = Date(
        title=_(u"Birth date"),
        description=_(u"(yyyy-mm-dd)"),
        required=False,
        )

    advisors = Attribute("""Advisors of the person""")

    advisees = Attribute("""Advisees of the person""")

    levels = Attribute("""Levels of the student""")


class IBasicPersonVocabulary(IVocabularyTokenized):
    """Marker interface for vocabularies that list basic persons."""


# XXX should be in skin or common, or more properly - core
class IGroupVocabulary(IVocabularyTokenized):
    """Marker interface for vocabularies that list schooltool groups."""


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

    def filter_key(key):
        """Return the subset of fields whose limited_keys list is either
           empty, or it contains the key passed"""

    def filter_keys(keys):
        """Return the subset of fields whose limited_keys list is either
           empty, or it contains one of the keys passed"""


class FilterKeyList(List):
    """Marker field to pin widgets on."""


class IFieldDescription(Interface):
    """Demographics field."""

    title = TextLine(
        title = _(u"Title"),
        description = _(u"As it should appear on forms and reports."))

    name = PythonIdentifier(
        title = _(u"ID"),
        description = _(u"A unique one word alphanumeric identifier."))

    description = TextLine(
        title = _(u"Description"),
        description = _(u"As it should appear on forms and reports."),
        required=False)

    required = Bool(
        title = _(u"Required"))

    limit_keys = FilterKeyList(
        title = _(u"Limit to group(s)"),
        description = _(u"If you select one or more groups below, this field "
                         "will only be displayed in forms and reports for "
                         "members of the selected groups."),
        value_type=Choice(
            source="schooltool.basicperson.limit_keys_vocabulary",
            required=True,
            ),
        required=False)


class EnumValueList(List):
    """Marker field to pin custom validation on."""


class IEnumFieldDescription(IFieldDescription):
    """Enumeration demographics field."""

    items = EnumValueList(
        title = _('Selection list'),
        description = _(u"Enter the valid values for the field below.  One "
                         "value per line.  These values will be displayed "
                         "as a menu in forms."))


class IIntFieldDescription(IFieldDescription):
    """Integer demographics field."""

    min_value = Int(
        title=_(u'Minimum value'),
        required=False)

    max_value = Int(
        title=_(u'Maximum value'),
        required=False)


class IFieldFilterVocabulary(IVocabularyTokenized):
    """Marker interface for vocabularies that give keys that are used
    to filter demographics fields for the context.
    """


class IAddEditViewTitle(Interface):
    """Demographics field add/edit view title."""


class ILimitKeysLabel(Interface):
    """Demographics field add/edit view limit keys label text."""


class ILimitKeysHint(Interface):
    """Demographics field add/edit view limit keys hint text."""

