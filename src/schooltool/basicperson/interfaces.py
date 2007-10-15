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
Lyceum person interfaces.

$Id$
"""
from zope.schema import Date
from zope.schema import Choice
from zope.schema import TextLine
from zope.interface import Interface
from zope.interface import Attribute
from zope.schema.interfaces import IIterableSource

from schooltool.demographics.interfaces import SourceList
from schooltool.common import SchoolToolMessage as _


class IBasicPerson(Interface):
    """Marker interface for Lyceum specific person."""

    first_name = TextLine(
        title=_(u"First name"),
        required=True,
        )

    last_name = TextLine(
        title=_(u"Last name"),
        required=True,
        )

    gender = Choice(
        title=_(u"Gender"),
        source=SourceList([_('male'), _('female')]),
        required=False,
        )

    email = TextLine(
        title=_(u"Email"),
        required=False,
        )

    phone = TextLine(
        title=_(u"Phone"),
        required=False,
        )

    gradeclass = Choice(
        title=_(u"Grade/Class", default="Group"),
        source="schooltool.basicperson.grade_class_source",
        required=False,
        )

    birth_date = Date(
        title=_(u"Birth date"),
        description=_(u"(yyyy-mm-dd)"),
        required=False,
        )

    advisor = Choice(
        title=_(u"Advisor"),
        source="schooltool.basicperson.advisor_source",
        required=False,
        )


class IBasicPersonSource(IIterableSource):
    """Marker interface for sources that list basic persons."""


# XXX should be in skin or common, or more properly - core
class IGroupSource(IIterableSource):
    """Marker interface for sources that list schooltool groups."""


class IStudent(Interface):

    advisor = Attribute("""Advisor of a student.""")


class IAdvisor(Interface):

    students = Attribute("""Students being advised by the advisor.""")

    def addStudent(student):
        """Add a student to the advised students list."""

    def removeStudent(student):
        """Remove this student from the advised students list."""
